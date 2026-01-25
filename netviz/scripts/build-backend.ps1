# NetViz 后端打包脚本
# 使用 PyInstaller 将后端打包为可执行文件

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$BackendDir = Join-Path $ProjectRoot "backend"
$OutputDir = Join-Path $ProjectRoot "src-tauri" "binaries"

Write-Host "=== NetViz Backend Build Script ===" -ForegroundColor Cyan
Write-Host "Backend Dir: $BackendDir"
Write-Host "Output Dir: $OutputDir"

# 确保输出目录存在
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

# 切换到后端目录
Push-Location $BackendDir

try {
    # 激活虚拟环境并运行 PyInstaller
    Write-Host "`nBuilding backend with PyInstaller..." -ForegroundColor Yellow
    
    & ".\.venv\Scripts\pyinstaller.exe" `
        --clean `
        --noconfirm `
        "netviz-backend.spec"

    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed"
    }

    # 复制输出文件到 Tauri binaries 目录
    $ExePath = Join-Path $BackendDir "dist" "netviz-backend-x86_64-pc-windows-msvc.exe"
    
    if (Test-Path $ExePath) {
        Write-Host "`nCopying binary to Tauri binaries directory..." -ForegroundColor Yellow
        Copy-Item $ExePath -Destination $OutputDir -Force
        Write-Host "Binary copied to: $OutputDir" -ForegroundColor Green
    } else {
        throw "Build output not found: $ExePath"
    }

    Write-Host "`n=== Build completed successfully! ===" -ForegroundColor Green
}
finally {
    Pop-Location
}
