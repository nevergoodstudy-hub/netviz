/**
 * Tauri 集成模块
 * 处理桌面应用和 Web 应用之间的差异
 */

// 检测是否在 Tauri 环境中运行
export const isTauri = (): boolean => {
  return typeof window !== 'undefined' && '__TAURI__' in window
}

// 获取 API 基础 URL
export const getApiBaseUrl = (): string => {
  if (isTauri()) {
    // Tauri 环境：使用本地后端
    return 'http://127.0.0.1:8000/api'
  }
  // Web 环境：使用相对路径（通过 Vite proxy）
  return '/api'
}

// 获取 WebSocket URL
export const getWsUrl = (): string => {
  if (isTauri()) {
    return 'ws://127.0.0.1:8000/ws'
  }
  // Web 环境
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/ws`
}

// Tauri 命令调用（如果可用）
export const invokeTauri = async <T>(cmd: string, args?: Record<string, unknown>): Promise<T | null> => {
  if (!isTauri()) return null
  
  try {
    const { invoke } = await import('@tauri-apps/api/core')
    return await invoke<T>(cmd, args)
  } catch (error) {
    console.error(`Failed to invoke Tauri command ${cmd}:`, error)
    return null
  }
}

// 启动后端服务
export const startBackend = async (): Promise<string | null> => {
  return invokeTauri<string>('start_backend')
}

// 停止后端服务
export const stopBackend = async (): Promise<string | null> => {
  return invokeTauri<string>('stop_backend')
}

// 检查后端状态
export const checkBackendStatus = async (): Promise<boolean> => {
  const result = await invokeTauri<boolean>('check_backend_status')
  return result ?? false
}

// 等待后端就绪
export const waitForBackend = async (timeout: number = 30000): Promise<boolean> => {
  const startTime = Date.now()
  const checkInterval = 500
  
  while (Date.now() - startTime < timeout) {
    try {
      const response = await fetch(`${getApiBaseUrl()}/health`)
      if (response.ok) {
        return true
      }
    } catch {
      // 后端还未就绪，继续等待
    }
    await new Promise(resolve => setTimeout(resolve, checkInterval))
  }
  
  return false
}
