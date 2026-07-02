# Sign Windows executables when signing credentials are configured.
# Set WINDOWS_SIGN_CERT_PATH and WINDOWS_SIGN_CERT_PASSWORD (PFX password).
# Optional: WINDOWS_SIGN_TIMESTAMP_URL (default: DigiCert).

param(
    [Parameter(Mandatory = $true)]
    [string[]]$Paths
)

$ErrorActionPreference = "Stop"

$certPath = $env:WINDOWS_SIGN_CERT_PATH
$certPassword = $env:WINDOWS_SIGN_CERT_PASSWORD
$timestampUrl = if ($env:WINDOWS_SIGN_TIMESTAMP_URL) {
    $env:WINDOWS_SIGN_TIMESTAMP_URL
} else {
    "http://timestamp.digicert.com"
}

if (-not $certPath -or -not (Test-Path $certPath)) {
    Write-Host "Skipping code signing (WINDOWS_SIGN_CERT_PATH not set)."
    exit 0
}

$signtool = @(
    "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\signtool.exe"
    "${env:ProgramFiles}\Windows Kits\10\bin\*\x64\signtool.exe"
) | ForEach-Object { Get-Item $_ -ErrorAction SilentlyContinue } |
    Sort-Object FullName -Descending |
    Select-Object -First 1

if (-not $signtool) {
    throw "signtool.exe not found. Install the Windows SDK signing tools."
}

$passwordArg = @()
if ($certPassword) {
    $passwordArg = @("/p", $certPassword)
}

foreach ($path in $Paths) {
    if (-not (Test-Path $path)) {
        throw "File not found for signing: $path"
    }
    Write-Host "Signing $path"
    & $signtool.FullName sign `
        /fd SHA256 `
        /f $certPath `
        @passwordArg `
        /tr $timestampUrl `
        /td SHA256 `
        $path
}

Write-Host "Signing complete."
