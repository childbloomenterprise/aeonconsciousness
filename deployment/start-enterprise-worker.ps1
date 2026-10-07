param(
    [string]$Python,
    [string]$PrivateRoot = "$env:LOCALAPPDATA\AEON\enterprise-private"
)
$ErrorActionPreference = 'Stop'
$aeonPrivateRoot = [System.IO.Path]::GetFullPath($PrivateRoot)
if (-not (Test-Path -LiteralPath (Join-Path $aeonPrivateRoot 'worker-connection.json'))) {
    throw 'Enroll a worker and save its connection outside the checkout first.'
}
if (-not $Python) { $Python = Join-Path $aeonPrivateRoot 'venv\Scripts\python.exe' }
$aeonPythonPath = (Resolve-Path -LiteralPath $Python).Path
& $aeonPythonPath -I -m aeon_enterprise.service --private-root $aeonPrivateRoot --check
if ($LASTEXITCODE -ne 0) { throw 'Worker installation check failed; repair Python, package, provider credentials or Chromium before starting.' }
$aeonArguments = @('-I', '-m', 'aeon_enterprise.service', '--private-root', ('"' + $aeonPrivateRoot + '"'))
$aeonProcess = Start-Process -FilePath $aeonPythonPath -ArgumentList $aeonArguments -WorkingDirectory $aeonPrivateRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $aeonPrivateRoot 'worker.log') -RedirectStandardError (Join-Path $aeonPrivateRoot 'worker-errors.log') -PassThru
Start-Sleep -Seconds 2
$aeonProcess.Refresh()
if ($aeonProcess.HasExited) { throw 'Worker exited during startup; inspect protected worker logs.' }
$aeonProcess | Select-Object Id,ProcessName
