param(
    [string]$Python,
    [string]$PrivateRoot = "$env:LOCALAPPDATA\AEON\enterprise-private"
)
$ErrorActionPreference = 'Stop'
$aeonPrivateRoot = [System.IO.Path]::GetFullPath($PrivateRoot)
if (-not (Test-Path -LiteralPath (Join-Path $aeonPrivateRoot 'worker-connection.json'))) {
    throw 'A protected worker connection is required before enabling startup.'
}
if (-not $Python) { $Python = Join-Path $aeonPrivateRoot 'venv\Scripts\python.exe' }
$aeonPythonPath = (Resolve-Path -LiteralPath $Python).Path
& $aeonPythonPath -I -m aeon_enterprise.service --private-root $aeonPrivateRoot --check
if ($LASTEXITCODE -ne 0) { throw 'Worker installation check failed; startup was not changed.' }
$aeonStarter = Join-Path $aeonPrivateRoot 'start-enterprise-worker.ps1'
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'start-enterprise-worker.ps1') -Destination $aeonStarter -Force
$aeonCommand = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + $aeonStarter + '" -Python "' + $aeonPythonPath + '" -PrivateRoot "' + $aeonPrivateRoot + '"'
$aeonVbs = "CreateObject(""WScript.Shell"").Run """ + $aeonCommand.Replace('"', '""') + """, 0, False`r`n"
$aeonStartup = [Environment]::GetFolderPath('Startup')
$aeonStartupFile = Join-Path $aeonStartup 'AEON Enterprise Worker.vbs'
Set-Content -LiteralPath $aeonStartupFile -Value $aeonVbs -Encoding ASCII
Write-Output 'AEON Enterprise worker will start hidden after this Windows user signs in.'
