# Build a shareable py-shimeji folder under dist/py-shimeji/
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install -q -r requirements-dev.txt
& .\.venv\Scripts\pyinstaller.exe --noconfirm --clean py-shimeji.spec
& .\.venv\Scripts\pyinstaller.exe --noconfirm --clean py-shimeji-updater.spec

Copy-Item -Force (Join-Path $ProjectRoot ".env.example") (Join-Path $ProjectRoot "dist\py-shimeji\.env.example")
Copy-Item -Force (Join-Path $ProjectRoot "dist\py-shimeji-updater.exe") (Join-Path $ProjectRoot "dist\py-shimeji\py-shimeji-updater.exe")

Write-Host ""
Write-Host "Build complete: dist\py-shimeji\py-shimeji.exe"
Write-Host "For release zip/installer use: .\scripts\build-release.ps1"
