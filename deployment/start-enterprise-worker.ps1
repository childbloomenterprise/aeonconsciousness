param(
    [Parameter(Mandatory=$true)][string]$Python,
    [string]$PrivateRoot = "$env:LOCALAPPDATA\AEON\enterprise-private"
)
$ErrorActionPreference = 'Stop'
$aeonPrivateRoot = [System.IO.Path]::GetFullPath($PrivateRoot)
$aeonRepository = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path -LiteralPath (Join-Path $aeonPrivateRoot 'worker-connection.json'))) {
    throw 'Enroll a worker and save its connection outside the checkout first.'
}
$aeonPythonPath = (Resolve-Path -LiteralPath $Python).Path
$aeonLauncher = Join-Path $PSScriptRoot 'run_enterprise_worker.py'
Start-Process -FilePath $aeonPythonPath -ArgumentList @('"' + $aeonLauncher + '"','--private-root','"' + $aeonPrivateRoot + '"') -WorkingDirectory $aeonRepository -WindowStyle Hidden -RedirectStandardOutput (Join-Path $aeonPrivateRoot 'worker.log') -RedirectStandardError (Join-Path $aeonPrivateRoot 'worker-errors.log') -PassThru | Select-Object Id,ProcessName
