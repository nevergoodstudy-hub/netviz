# NetViz 后端打包脚本
# 使用 PyInstaller 将后端打包为可执行文件

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$BackendDir = Join-Path $ProjectRoot "backend"
$BuildScript = Join-Path $ProjectRoot "scripts" "build_backend_sidecar.py"
$TargetTriple = if ($env:NETVIZ_TARGET_TRIPLE) { $env:NETVIZ_TARGET_TRIPLE } else { "x86_64-pc-windows-msvc" }

Write-Host "=== NetViz Backend Build Script ===" -ForegroundColor Cyan
Write-Host "Backend Dir: $BackendDir"
Write-Host "Target Triple: $TargetTriple"

# 切换到后端目录
Push-Location $BackendDir

try {
    Write-Host "`nBuilding backend sidecar..." -ForegroundColor Yellow

    & ".\.venv\Scripts\python.exe" `
        $BuildScript `
        --target `
        $TargetTriple

    if ($LASTEXITCODE -ne 0) {
        throw "Backend sidecar build failed"
    }

    Write-Host "`n=== Build completed successfully! ===" -ForegroundColor Green
}
finally {
    Pop-Location
}
