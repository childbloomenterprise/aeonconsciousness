param(
    [string]$PythonExecutable = 'python',
    [string]$EnvironmentPath = '',
    [switch]$Offline,
    [switch]$Probe
)

$ErrorActionPreference = 'Stop'
$releaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
if (-not $EnvironmentPath) {
    $EnvironmentPath = Join-Path $releaseRoot '.aeon-venv'
}
$EnvironmentPath = [System.IO.Path]::GetFullPath($EnvironmentPath)
$wheelPath = Join-Path $releaseRoot 'dist\codebee_improve-0.3.0-py3-none-any.whl'
if (-not (Test-Path -LiteralPath $wheelPath)) {
    throw 'Release wheel missing. Run this script from extracted AEON release bundle.'
}
$version = & $PythonExecutable -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'
if ($LASTEXITCODE -ne 0) { throw 'Python unavailable. Pass -PythonExecutable with full path to Python.' }
if ($Offline -and $version -ne '3.11') {
    throw 'Bundled offline dependencies support Windows x64 Python 3.11. Use online install for other versions.'
}
if (-not (Test-Path -LiteralPath (Join-Path $EnvironmentPath 'Scripts\python.exe'))) {
    & $PythonExecutable -m venv $EnvironmentPath
    if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
}
$workerPython = Join-Path $EnvironmentPath 'Scripts\python.exe'
$pipArguments = @('-m', 'pip', 'install', '--disable-pip-version-check', '--timeout', '30', '--retries', '2', '-c', (Join-Path $PSScriptRoot 'requirements.txt'))
if ($Offline) {
    $pipArguments += @('--no-index', '--find-links', (Join-Path $releaseRoot 'wheelhouse'))
}
$pipArguments += "$wheelPath[deployment]"
& $workerPython @pipArguments
if ($LASTEXITCODE -ne 0) { throw 'AEON dependency installation failed.' }
if ($Offline) {
    & $workerPython -c 'from pathlib import Path; from playwright.sync_api import sync_playwright; p=sync_playwright().start(); exists=Path(p.chromium.executable_path).is_file(); p.stop(); raise SystemExit(0 if exists else 1)'
    if ($LASTEXITCODE -ne 0) { throw 'Matching Chromium not cached. Run online install once; browser binaries are not bundled.' }
} else {
    & $workerPython -m playwright install chromium
    if ($LASTEXITCODE -ne 0) { throw 'Chromium installation failed.' }
}
& $workerPython -m aeon_worker smoke --workspace (Join-Path $releaseRoot '.aeon-output\installation-check')
if ($LASTEXITCODE -ne 0) { throw 'AEON installation smoke check failed.' }
if ($Probe) {
    & $workerPython -m aeon_worker doctor --probe
} else {
    & $workerPython -m aeon_worker doctor
}
if ($LASTEXITCODE -ne 0) { throw 'AEON provider readiness probe failed.' }
Write-Output "AEON installed. Command: $EnvironmentPath\Scripts\aeon.exe"
