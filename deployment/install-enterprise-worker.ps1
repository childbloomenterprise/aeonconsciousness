param(
    [Parameter(Mandatory=$true)][string]$ReleaseWheel,
    [string]$Uv = 'uv',
    [string]$PrivateRoot = "$env:LOCALAPPDATA\AEON\enterprise-private"
)
$ErrorActionPreference = 'Stop'
$aeonWheel = (Resolve-Path -LiteralPath $ReleaseWheel).Path
if ([System.IO.Path]::GetExtension($aeonWheel) -ne '.whl') { throw 'Supply a built AEON release wheel.' }
$aeonPrivateRoot = [System.IO.Path]::GetFullPath($PrivateRoot)
New-Item -ItemType Directory -Path $aeonPrivateRoot -Force | Out-Null
$aeonIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
& icacls.exe $aeonPrivateRoot /grant:r "$($aeonIdentity):(OI)(CI)F" /inheritance:r | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Could not restrict private installation access.' }
$aeonVenv = Join-Path $aeonPrivateRoot 'venv'
$aeonVenvPython = Join-Path $aeonVenv 'Scripts\python.exe'
$aeonRunning = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.ExecutablePath -eq $aeonVenvPython -and $_.CommandLine -match 'aeon_enterprise\.service' }
if ($aeonRunning) { throw 'Stop this installation''s supervisor before updating its runtime.' }
$aeonOldPythonDirectory = $env:UV_PYTHON_INSTALL_DIR
$aeonOldBrowsers = $env:PLAYWRIGHT_BROWSERS_PATH
try {
    $env:UV_PYTHON_INSTALL_DIR = Join-Path $aeonPrivateRoot 'python'
    & $Uv python install 3.11 --no-bin --no-registry
    if ($LASTEXITCODE -ne 0) { throw 'Dedicated Python installation failed.' }
    $aeonBasePython = & $Uv python find 3.11 --managed-python
    if ($LASTEXITCODE -ne 0) { throw 'Dedicated Python lookup failed.' }
    if (-not (Test-Path -LiteralPath $aeonVenvPython)) {
        & $Uv venv $aeonVenv --python $aeonBasePython --seed
        if ($LASTEXITCODE -ne 0) { throw 'Dedicated virtual environment creation failed.' }
    }
    & $aeonVenvPython -m pip install --force-reinstall ($aeonWheel + '[deployment]')
    if ($LASTEXITCODE -ne 0) { throw 'AEON package installation failed.' }
    $env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $aeonPrivateRoot 'browsers'
    & $aeonVenvPython -m playwright install chromium
    if ($LASTEXITCODE -ne 0) { throw 'Private Chromium installation failed.' }
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'start-enterprise-worker.ps1') -Destination (Join-Path $aeonPrivateRoot 'start-enterprise-worker.ps1') -Force
    Write-Output 'Installed AEON worker outside the checkout. Enroll/configure credentials before starting.'
} finally {
    $env:UV_PYTHON_INSTALL_DIR = $aeonOldPythonDirectory
    $env:PLAYWRIGHT_BROWSERS_PATH = $aeonOldBrowsers
}
