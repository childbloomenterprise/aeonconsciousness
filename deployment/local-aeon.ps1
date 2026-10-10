param(
    [ValidateSet('start','status','stop','restart')][string]$Action = 'start',
    [string]$StateRoot = $env:AEON_LOCAL_STATE_DIR,
    [int]$Port = 8787,
    [string]$Python = "$env:LOCALAPPDATA\AEON\enterprise-private\venv\Scripts\python.exe",
    [string]$ProviderFile = "$env:LOCALAPPDATA\AEON\enterprise-private\providers.json",
    [string]$Browsers = "$env:LOCALAPPDATA\AEON\enterprise-private\browsers",
    [string]$Node,
    [switch]$ConsoleOnly
)
$ErrorActionPreference = 'Stop'
if (-not $PSBoundParameters.ContainsKey('Port') -and $env:AEON_LOCAL_PORT) { $Port = [int]$env:AEON_LOCAL_PORT }
if ($Port -lt 1024 -or $Port -gt 65535) { throw 'Use a local port from 1024 through 65535.' }
if (-not $StateRoot) { $StateRoot = "$env:LOCALAPPDATA\AEON\localhost-private" }
$aeonRoot = [IO.Path]::GetFullPath($StateRoot).TrimEnd('\')
$aeonHostedRoot = [IO.Path]::GetFullPath("$env:LOCALAPPDATA\AEON\enterprise-private").TrimEnd('\')
if ($aeonRoot -eq $aeonHostedRoot -or $aeonRoot.StartsWith($aeonHostedRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Local state must remain separate from hosted worker configuration.' }
$aeonSource = Split-Path -Parent $PSScriptRoot
$aeonEnterprise = Join-Path $aeonSource 'enterprise'
$aeonOrigin = "http://127.0.0.1:$Port"
$aeonRegistryPath = Join-Path $aeonRoot 'processes.json'

function Get-AeonProcess($record, $kind) {
    if (-not $record) { return $null }
    $current = Get-CimInstance Win32_Process -Filter "ProcessId=$($record.pid)" -ErrorAction SilentlyContinue
    if (-not $current -or $current.ExecutablePath -ne $record.executable) { return $null }
    $signature = if ($kind -eq 'server') { 'scripts/dev.mjs' } else { 'aeon_enterprise.local_service' }
    if (-not $current.CommandLine.Contains($signature)) { return $null }
    if ($kind -eq 'worker' -and -not $current.CommandLine.Contains($aeonRoot)) { return $null }
    # PowerShell 7 parses ISO dates from JSON; Windows PowerShell 5 keeps strings.
    $expectedCreated = if ($record.created -is [datetime]) { $record.created.ToUniversalTime().ToString('o') } else { [string]$record.created }
    if ($current.CreationDate.ToUniversalTime().ToString('o') -ne $expectedCreated) { return $null }
    return $current
}
function Get-AeonRegistry {
    if (Test-Path -LiteralPath $aeonRegistryPath) { return Get-Content -LiteralPath $aeonRegistryPath -Raw | ConvertFrom-Json }
    return $null
}
function Get-AeonStatus {
    $registry = Get-AeonRegistry
    $statusOrigin = $aeonOrigin
    if ($registry.origin -match '^http://127\.0\.0\.1:[0-9]+$') { $statusOrigin = $registry.origin }
    $runtime = $null
    try { $runtime = Invoke-RestMethod -Uri "$statusOrigin/api/local/runtime" -TimeoutSec 3 } catch { }
    [pscustomobject]@{ url=$statusOrigin; server_running=[bool](Get-AeonProcess $registry.server 'server'); worker_running=[bool](Get-AeonProcess $registry.worker 'worker'); persistent=[bool]($runtime -and $runtime.persistence); mode=$runtime.mode; state=$aeonRoot }
}
function Stop-AeonLocal {
    $registry = Get-AeonRegistry
    foreach ($kind in @('worker','server')) {
        $current = Get-AeonProcess $registry.$kind $kind
        if ($current) {
            & taskkill.exe /PID $current.ProcessId /T /F | Out-Null
            if ($LASTEXITCODE -ne 0) { throw "Could not stop local $kind process." }
        }
    }
    if (Test-Path -LiteralPath $aeonRegistryPath) { Remove-Item -LiteralPath $aeonRegistryPath -Force }
}
if ($Action -eq 'status') { Get-AeonStatus; exit 0 }
if ($Action -eq 'stop') { Stop-AeonLocal; Get-AeonStatus; exit 0 }
if ($Action -eq 'restart') { Stop-AeonLocal }
$aeonExisting = Get-AeonStatus
if ($aeonExisting.server_running -or $aeonExisting.worker_running) { $aeonExisting; Write-Output 'Local process already active. Use restart to apply code changes or launch missing components.'; exit 0 }
New-Item -ItemType Directory -Path $aeonRoot -Force | Out-Null
$aeonIdentity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
& icacls.exe $aeonRoot /grant:r "$($aeonIdentity):(OI)(CI)F" /inheritance:r | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Could not protect local credentials and logs.' }
if (-not $Node) {
    $aeonBundledNode = "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
    $Node = if (Test-Path -LiteralPath $aeonBundledNode) { $aeonBundledNode } else { (Get-Command node -ErrorAction Stop).Source }
}
$aeonNodePath = (Resolve-Path -LiteralPath $Node).Path
$aeonNodeVersion = & $aeonNodePath -p 'process.versions.node.split(String.fromCharCode(46))[0]'
if ($LASTEXITCODE -ne 0 -or [int]$aeonNodeVersion -lt 24) { throw 'Node.js24 or newer required for persistent SQLite preview.' }
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) { throw "Port $Port already used. Stop its existing process or choose another port." }
$aeonWorkerArgs = @('-m','aeon_enterprise.local_service','--origin',$aeonOrigin,'--state-root',('"' + (Join-Path $aeonRoot 'worker') + '"'),'--provider-file',('"' + $ProviderFile + '"'),'--browsers',('"' + $Browsers + '"'))
if (-not $ConsoleOnly) {
    $aeonPythonPath = (Resolve-Path -LiteralPath $Python).Path
    Push-Location $aeonSource
    try {
        & $aeonPythonPath -m aeon_enterprise.local_service --origin $aeonOrigin --state-root (Join-Path $aeonRoot 'worker') --provider-file $ProviderFile --browsers $Browsers --check
        if ($LASTEXITCODE -ne 0) { throw 'Local worker check failed; configure model credentials or Chromium. Use -ConsoleOnly for UI-only preview.' }
    } finally { Pop-Location }
}
Push-Location $aeonEnterprise
try { & $aeonNodePath scripts/build.mjs; if ($LASTEXITCODE -ne 0) { throw 'Local enterprise build failed. Install enterprise npm dependencies first.' } } finally { Pop-Location }
$aeonOldRoot = $env:AEON_LOCAL_STATE_DIR
$aeonOldPort = $env:AEON_LOCAL_PORT
$aeonServer = $null
$aeonWorker = $null
try {
    $env:AEON_LOCAL_STATE_DIR = $aeonRoot
    $env:AEON_LOCAL_PORT = [string]$Port
    $aeonServer = Start-Process -FilePath $aeonNodePath -ArgumentList @('scripts/dev.mjs') -WorkingDirectory $aeonEnterprise -WindowStyle Hidden -RedirectStandardOutput (Join-Path $aeonRoot 'server.log') -RedirectStandardError (Join-Path $aeonRoot 'server-errors.log') -PassThru
    $aeonReady = $false
    for ($attempt=0; $attempt -lt 30; $attempt++) {
        Start-Sleep -Milliseconds 500
        $aeonServer.Refresh()
        if ($aeonServer.HasExited) { throw 'Local server exited. Inspect protected server-errors.log.' }
        try { $runtime = Invoke-RestMethod -Uri "$aeonOrigin/api/local/runtime" -TimeoutSec 2; if ($runtime.mode -eq 'local' -and $runtime.persistence) { $aeonReady=$true; break } } catch { }
    }
    if (-not $aeonReady) { throw 'Persistent localhost runtime did not become ready.' }
    if (-not $ConsoleOnly) {
        $aeonWorker = Start-Process -FilePath $aeonPythonPath -ArgumentList $aeonWorkerArgs -WorkingDirectory $aeonSource -WindowStyle Hidden -RedirectStandardOutput (Join-Path $aeonRoot 'worker.log') -RedirectStandardError (Join-Path $aeonRoot 'worker-errors.log') -PassThru
        Start-Sleep -Seconds 2
        $aeonWorker.Refresh()
        if ($aeonWorker.HasExited) { throw 'Local supervisor exited. Inspect protected worker-errors.log.' }
    }
    $aeonRecords = @{origin=$aeonOrigin}
    foreach ($pair in @(@('server',$aeonServer),@('worker',$aeonWorker))) {
        if ($pair[1]) {
            $current = Get-CimInstance Win32_Process -Filter "ProcessId=$($pair[1].Id)"
            $aeonRecords[$pair[0]] = @{pid=$current.ProcessId; executable=$current.ExecutablePath; created=$current.CreationDate.ToUniversalTime().ToString('o')}
        }
    }
    $aeonRecords | ConvertTo-Json | Set-Content -LiteralPath $aeonRegistryPath -Encoding UTF8
    Get-AeonStatus
} catch {
    foreach ($process in @($aeonWorker,$aeonServer)) { if ($process -and -not $process.HasExited) { & taskkill.exe /PID $process.Id /T /F | Out-Null } }
    throw
} finally {
    $env:AEON_LOCAL_STATE_DIR = $aeonOldRoot
    $env:AEON_LOCAL_PORT = $aeonOldPort
}
