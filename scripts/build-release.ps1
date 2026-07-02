# Build release artifacts: app folder, portable zip, optional signed installer.
param(
    [switch]$Installer,
    [switch]$Sign
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install -q -r requirements-dev.txt

$version = (& .\.venv\Scripts\python.exe -c "from version import __version__; print(__version__)").Trim()

& .\.venv\Scripts\pyinstaller.exe --noconfirm --clean py-shimeji.spec
& .\.venv\Scripts\pyinstaller.exe --noconfirm --clean py-shimeji-updater.spec

Copy-Item -Force (Join-Path $ProjectRoot ".env.example") (Join-Path $ProjectRoot "dist\py-shimeji\.env.example")
Copy-Item -Force (Join-Path $ProjectRoot "dist\py-shimeji-updater.exe") (Join-Path $ProjectRoot "dist\py-shimeji\py-shimeji-updater.exe")

$appDir = Join-Path $ProjectRoot "dist\py-shimeji"
$zipPath = Join-Path $ProjectRoot "dist\py-shimeji-$version.zip"

if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}
Compress-Archive -Path $appDir -DestinationPath $zipPath

$signPaths = @(
    (Join-Path $appDir "py-shimeji.exe"),
    (Join-Path $appDir "py-shimeji-updater.exe")
)

if ($Sign -or $env:WINDOWS_SIGN_CERT_PATH) {
    & (Join-Path $PSScriptRoot "sign.ps1") -Paths $signPaths
}

$installerPath = $null
if ($Installer) {
    $iscc = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
        "${env:LocalAppData}\Programs\Inno Setup 6\ISCC.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1

    if (-not $iscc) {
        throw "Inno Setup 6 (iscc.exe) not found. Install from https://jrsoftware.org/isinfo.php"
    }

    & $iscc "/DAppVersion=$version" (Join-Path $PSScriptRoot "installer.iss")
    $installerPath = Join-Path $ProjectRoot "dist\py-shimeji-setup-$version.exe"

    if ($Sign -or $env:WINDOWS_SIGN_CERT_PATH) {
        & (Join-Path $PSScriptRoot "sign.ps1") -Paths @($installerPath)
    }
}

Write-Host ""
Write-Host "Release build complete (v$version)"
Write-Host "  Portable folder: dist\py-shimeji\"
Write-Host "  Portable zip:    dist\py-shimeji-$version.zip"
if ($installerPath) {
    Write-Host "  Installer:       dist\py-shimeji-setup-$version.exe"
}
