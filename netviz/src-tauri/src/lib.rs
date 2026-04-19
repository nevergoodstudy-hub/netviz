use tauri::AppHandle;
use tauri_plugin_shell::ShellExt;
use serde::Deserialize;
use std::sync::atomic::{AtomicBool, Ordering};

// 全局后端进程状态
static BACKEND_RUNNING: AtomicBool = AtomicBool::new(false);

#[derive(Clone, Deserialize)]
struct BackendEndpointFile {
    desktop: DesktopBackendEndpoint,
}

#[derive(Clone, Deserialize)]
struct DesktopBackendEndpoint {
    protocol: String,
    host: String,
    port: u16,
    #[serde(rename = "apiBasePath")]
    api_base_path: String,
}

impl DesktopBackendEndpoint {
    fn origin(&self) -> String {
        format!("{}://{}:{}", self.protocol, self.host, self.port)
    }

    fn api_base_url(&self) -> String {
        format!("{}{}", self.origin(), normalize_path(&self.api_base_path))
    }

    fn health_url(&self) -> String {
        format!("{}/health", self.api_base_url().trim_end_matches('/'))
    }
}

fn normalize_path(path: &str) -> String {
    if path.is_empty() || path == "/" {
        "/".to_string()
    } else if path.starts_with('/') {
        path.to_string()
    } else {
        format!("/{}", path)
    }
}

fn backend_endpoint() -> Result<DesktopBackendEndpoint, String> {
    serde_json::from_str::<BackendEndpointFile>(include_str!("../../config/backend-endpoint.json"))
        .map(|config| config.desktop)
        .map_err(|err| format!("Failed to parse backend endpoint config: {}", err))
}

/// 检查后端健康状态
#[tauri::command]
async fn check_backend_health() -> Result<bool, String> {
    let endpoint = backend_endpoint()?;

    match reqwest::get(endpoint.health_url()).await {
        Ok(response) => Ok(response.status().is_success()),
        Err(_) => Ok(false),
    }
}

/// 获取后端 API 地址
#[tauri::command]
fn get_backend_url() -> Result<String, String> {
    Ok(backend_endpoint()?.origin())
}

/// 启动后端 sidecar
async fn start_backend_sidecar(app: &AppHandle) -> Result<(), String> {
    if BACKEND_RUNNING.load(Ordering::SeqCst) {
        println!("[Tauri] Backend already started");
        return Ok(());
    }

    println!("[Tauri] Starting backend sidecar...");

    let endpoint = backend_endpoint()?;

    let sidecar = app
        .shell()
        .sidecar("netviz-backend")
        .map(|command| {
            command
                .env("NETVIZ_HOST", endpoint.host.clone())
                .env("NETVIZ_PORT", endpoint.port.to_string())
        })
        .map_err(|e| format!("Failed to create sidecar: {}", e))?;

    let (mut rx, _child) = sidecar
        .spawn()
        .map_err(|e| format!("Failed to spawn sidecar: {}", e))?;

    BACKEND_RUNNING.store(true, Ordering::SeqCst);
    println!("[Tauri] Backend sidecar started");

    // 在后台监听输出
    tauri::async_runtime::spawn(async move {
        use tauri_plugin_shell::process::CommandEvent;
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line) => {
                    let msg = String::from_utf8_lossy(&line);
                    if !msg.trim().is_empty() {
                        println!("[Backend] {}", msg);
                    }
                }
                CommandEvent::Stderr(line) => {
                    let msg = String::from_utf8_lossy(&line);
                    if !msg.trim().is_empty() {
                        eprintln!("[Backend] {}", msg);
                    }
                }
                CommandEvent::Error(err) => {
                    eprintln!("[Backend Error] {}", err);
                }
                CommandEvent::Terminated(payload) => {
                    println!("[Backend] Process terminated with code: {:?}", payload.code);
                    BACKEND_RUNNING.store(false, Ordering::SeqCst);
                    break;
                }
                _ => {}
            }
        }
    });

    // 等待后端就绪
    for i in 0..30 {
        tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
        if let Ok(true) = check_backend_health().await {
            println!("[Tauri] Backend is ready (attempt {})", i + 1);
            return Ok(());
        }
    }

    Err("Backend failed to start within timeout".to_string())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            check_backend_health,
            get_backend_url
        ])
        .setup(|app| {
            let handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                if let Err(e) = start_backend_sidecar(&handle).await {
                    eprintln!("[Tauri] Failed to start backend: {}", e);
                }
            });
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
