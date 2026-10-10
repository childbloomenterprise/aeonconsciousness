param(
    [Parameter(Mandatory)][ValidateSet('backup','restore')][string]$Action,
    [Parameter(Mandatory)][string]$ArchivePath,
    [string]$StateRoot,
    [string]$RestoreRoot,
    [ValidateRange(1024,65535)][int]$Port = 8787,
    [ValidateRange(1,512)][int]$MaxMegabytes = 128
)
# Owner-private, same-Windows-account/machine recovery. Never stops a process.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
Add-Type -AssemblyName System.Security
Add-Type -AssemblyName System.IO.Compression
try { Add-Type -AssemblyName System.Security.Cryptography.ProtectedData -ErrorAction SilentlyContinue } catch { }
$limit = [long]$MaxMegabytes * 1MB
$repo = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot)).TrimEnd('\')
$hosted = [IO.Path]::GetFullPath("$env:LOCALAPPDATA\AEON\enterprise-private").TrimEnd('\')
$reserved = '_aeon_snapshot_manifest.json'
$entropy = [Text.Encoding]::UTF8.GetBytes('AEON local-state snapshot v1')
$scope = [Security.Cryptography.DataProtectionScope]::CurrentUser
function FullPath([string]$path) {
    if ($path -notmatch '^[A-Za-z]:[\\/]') { throw 'Use explicit absolute local-drive paths.' }
    return [IO.Path]::GetFullPath($path).TrimEnd('\')
}
function Within([string]$child,[string]$parent) {
    return $child.Equals($parent,[StringComparison]::OrdinalIgnoreCase) -or $child.StartsWith($parent+'\',[StringComparison]::OrdinalIgnoreCase)
}
function SafeAncestors([string]$path) {
    $current = $path
    while ($current) {
        if (Test-Path -LiteralPath $current) {
            if ((Get-Item -LiteralPath $current -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Reparse-point paths are not supported.' }
        }
        $next = Split-Path -Parent $current
        if ($next -eq $current) { break }
        $current = $next
    }
}
function PrivateAcl([string]$path) {
    $owner = [Security.Principal.WindowsIdentity]::GetCurrent().User
    $system = [Security.Principal.SecurityIdentifier]::new('S-1-5-18')
    $directory = (Get-Item -LiteralPath $path -Force).PSIsContainer
    $acl = if ($directory) { [Security.AccessControl.DirectorySecurity]::new() } else { [Security.AccessControl.FileSecurity]::new() }
    $acl.SetOwner($owner); $acl.SetAccessRuleProtection($true,$false)
    foreach ($sid in @($owner,$system)) {
        $rule = if ($directory) { [Security.AccessControl.FileSystemAccessRule]::new($sid,'FullControl','ContainerInherit,ObjectInherit','None','Allow') } else { [Security.AccessControl.FileSystemAccessRule]::new($sid,'FullControl','Allow') }
        $acl.AddAccessRule($rule)
    }
    Set-Acl -LiteralPath $path -AclObject $acl
}
function Inventory([string]$root) {
    $items = @(Get-ChildItem -LiteralPath $root -Recurse -Force)
    if ($items.Count -gt 20000) { throw 'State exceeds 20,000 entries.' }
    foreach ($item in $items) {
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'State contains a reparse point.' }
    }
    return $items
}
function AssertStopped([string]$root,[int]$defaultPort) {
    $ports = @($defaultPort)
    $registryPath = Join-Path $root 'processes.json'
    if (Test-Path -LiteralPath $registryPath) {
        $registry = Get-Content -LiteralPath $registryPath -Raw | ConvertFrom-Json
        if ($registry.PSObject.Properties.Name -contains 'origin') {
            if ([string]$registry.origin -notmatch '^http://127\.0\.0\.1:([0-9]+)$') { throw 'Registry origin is invalid; stopped state uncertain.' }
            $ports += [int]$Matches[1]
        }
        foreach ($kind in @('server','worker')) {
            if ($registry.PSObject.Properties.Name -contains $kind -and $registry.$kind) {
                $record = $registry.$kind
                if (-not ($record.PSObject.Properties.Name -contains 'pid') -or [int]$record.pid -le 0) { throw 'Registry process identity is invalid.' }
                # Any live recorded PID is conservatively refused, including PID reuse.
                if (Get-CimInstance Win32_Process -Filter "ProcessId=$([int]$record.pid)") { throw 'Recorded process remains live or its identity is ambiguous. Stop and verify separately.' }
            }
        }
    }
    $processes = @(Get-CimInstance Win32_Process)
    foreach ($process in $processes) {
        $command = [string]$process.CommandLine
        if ($command.IndexOf($root,[StringComparison]::OrdinalIgnoreCase) -ge 0 -and $command -match 'aeon_(?:enterprise|worker)') { throw 'Source worker/job process remains live.' }
    }
    # Any listener refuses the snapshot; no HTTP success/authentication assumption.
    $listeners = @(Get-NetTCPConnection -State Listen -ErrorAction Stop)
    foreach ($checkPort in ($ports | Select-Object -Unique)) {
        if ($checkPort -lt 1024 -or $checkPort -gt 65535) { throw 'Registry port is invalid.' }
        if ($listeners | Where-Object LocalPort -eq $checkPort) { throw 'Local server port remains live. Stop and verify separately.' }
        $client = [Net.Sockets.TcpClient]::new()
        try {
            $pending = $client.BeginConnect('127.0.0.1',$checkPort,$null,$null)
            if (-not $pending.AsyncWaitHandle.WaitOne(5000)) { throw 'Local server reachability uncertain; snapshot refused.' }
            try { $client.EndConnect($pending) } catch [Net.Sockets.SocketException] {
                if ($_.Exception.SocketErrorCode -eq [Net.Sockets.SocketError]::ConnectionRefused) { continue }
                throw 'Local server reachability uncertain; snapshot refused.'
            }
            throw 'Local server responds; snapshot refused.'
        } finally { $client.Dispose() }
    }
}
function EntryPath([string]$name) {
    if (-not $name -or $name.Contains('\') -or $name.StartsWith('/') -or $name.Contains(':')) { throw 'Unsafe archive entry path.' }
    $parts = $name.TrimEnd('/').Split('/')
    foreach ($part in $parts) {
        if (-not $part -or $part -eq '.' -or $part -eq '..' -or $part -match '[<>:"|?*\x00-\x1f]' -or $part.EndsWith('.') -or $part.EndsWith(' ') -or $part -match '^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)') { throw 'Unsafe archive entry component.' }
    }
    return $name.Replace('/',[IO.Path]::DirectorySeparatorChar)
}
function HashBytes([byte[]]$bytes) {
    $hash = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($hash.ComputeHash($bytes))).Replace('-','').ToLowerInvariant() } finally { $hash.Dispose() }
}
function HashStream($stream,[long]$maximum) {
    $hash=[Security.Cryptography.SHA256]::Create(); $buffer=New-Object byte[] 65536; $used=0L
    try {
        while (($count=$stream.Read($buffer,0,$buffer.Length)) -gt 0) {
            $used += $count
            if ($used -gt $maximum) { throw 'Decompressed entry exceeds declared size limit.' }
            $null=$hash.TransformBlock($buffer,0,$count,$buffer,0)
        }
        $null=$hash.TransformFinalBlock([byte[]]@(),0,0)
        return ([BitConverter]::ToString($hash.Hash)).Replace('-','').ToLowerInvariant()
    } finally { $hash.Dispose() }
}
$archive = FullPath $ArchivePath
if (Within $archive $repo) { throw 'Backup archive must stay outside the repository.' }
SafeAncestors $archive
$ancestor = Split-Path -Parent $archive
while ($ancestor) {
    if (Test-Path -LiteralPath (Join-Path $ancestor '.git')) { throw 'Backup archive must stay outside Git repositories.' }
    $next = Split-Path -Parent $ancestor; if ($next -eq $ancestor) { break }; $ancestor = $next
}
$memory = [IO.MemoryStream]::new()
$zip = $null
$handles = @()
try {
    if ($Action -eq 'backup') {
        if (-not $StateRoot) { $StateRoot = "$env:LOCALAPPDATA\AEON\localhost-private" }
        $root = FullPath $StateRoot
        SafeAncestors $root
        if (-not (Test-Path -LiteralPath $root -PathType Container)) { throw 'Source state directory missing.' }
        if ((Within $root $hosted) -or (Within $hosted $root) -or (Within $archive $root)) { throw 'Source/archive must remain separate from hosted state.' }
        if (Test-Path -LiteralPath $archive) { throw 'Archive already exists; overwrite refused.' }
        if (-not (Test-Path -LiteralPath (Split-Path -Parent $archive) -PathType Container)) { throw 'Archive parent directory must already exist.' }
        AssertStopped $root $Port
        $items = @(Inventory $root)
        $files = @($items | Where-Object { -not $_.PSIsContainer })
        if (($files | Measure-Object Length -Sum).Sum -gt $limit) { throw 'Source state exceeds size limit.' }
        if ($items | Where-Object { $_.FullName.Substring($root.Length+1) -eq $reserved }) { throw 'Reserved manifest name exists in source.' }
        foreach ($file in $files) { $handles += [IO.File]::Open($file.FullName,'Open','Read','Read') }
        $zip = [IO.Compression.ZipArchive]::new($memory,[IO.Compression.ZipArchiveMode]::Create,$true)
        $records = @()
        for ($index=0; $index -lt $files.Count; $index++) {
            $file = $files[$index]; $stream = $handles[$index]
            $name = $file.FullName.Substring($root.Length+1).Replace('\','/')
            $null = EntryPath $name
            $hash = [Security.Cryptography.SHA256]::Create()
            try { $digest = ([BitConverter]::ToString($hash.ComputeHash($stream))).Replace('-','').ToLowerInvariant() } finally { $hash.Dispose() }
            $stream.Position=0
            $entry = $zip.CreateEntry($name,[IO.Compression.CompressionLevel]::Optimal)
            $output = $entry.Open(); try { $stream.CopyTo($output) } finally { $output.Dispose() }
            $records += @{path=$name; bytes=$stream.Length; sha256=$digest}
            if ($memory.Length -gt $limit) { throw 'Archive exceeds size limit.' }
        }
        $directories = @($items | Where-Object PSIsContainer | ForEach-Object { $_.FullName.Substring($root.Length+1).Replace('\','/')+'/' })
        foreach ($name in $directories) { $null=EntryPath $name; $null=$zip.CreateEntry($name) }
        $manifest = @{version=1; source=$root; port=$Port; files=$records; directories=$directories; created=[DateTime]::UtcNow.ToString('o')}
        $entry = $zip.CreateEntry($reserved)
        $writer = [IO.StreamWriter]::new($entry.Open(),[Text.UTF8Encoding]::new($false))
        try { $writer.Write(($manifest | ConvertTo-Json -Depth 6 -Compress)) } finally { $writer.Dispose() }
        $zip.Dispose(); $zip=$null
        if ($memory.Length -gt $limit) { throw 'Archive exceeds size limit.' }
        AssertStopped $root $Port
        $after = @(Inventory $root)
        $beforeNames = (@($items | ForEach-Object FullName | Sort-Object) -join "`n")
        $afterNames = (@($after | ForEach-Object FullName | Sort-Object) -join "`n")
        if ($beforeNames -cne $afterNames) { throw 'Source inventory changed during backup.' }
        $encrypted = [Security.Cryptography.ProtectedData]::Protect($memory.ToArray(),$entropy,$scope)
        $dest = [IO.File]::Open($archive,'CreateNew','Write','None')
        try { PrivateAcl $archive; $dest.Write($encrypted,0,$encrypted.Length); $dest.Flush($true) } finally { $dest.Dispose() }
        [pscustomobject]@{action='backup'; files=$records.Count; encrypted_bytes=$encrypted.Length; sha256=(HashBytes $encrypted); scope='Windows CurrentUser DPAPI; same account/machine'} | ConvertTo-Json -Compress
    } else {
        if (-not $RestoreRoot) { throw 'Explicit new empty RestoreRoot required.' }
        $target = FullPath $RestoreRoot
        SafeAncestors $target
        if ((Within $target $hosted) -or (Within $hosted $target) -or (Within $archive $target)) { throw 'Restore must remain separate from hosted state/archive.' }
        if (-not (Test-Path -LiteralPath $archive -PathType Leaf) -or (Get-Item -LiteralPath $archive).Length -gt ($limit+1MB)) { throw 'Archive missing or exceeds size limit.' }
        try { $plain = [Security.Cryptography.ProtectedData]::Unprotect([IO.File]::ReadAllBytes($archive),$entropy,$scope) } catch { throw 'DPAPI decryption/integrity failed; restore refused.' }
        if ($plain.Length -gt $limit) { throw 'Decrypted archive exceeds size limit.' }
        $memory.Write($plain,0,$plain.Length); $memory.Position=0
        $zip = [IO.Compression.ZipArchive]::new($memory,[IO.Compression.ZipArchiveMode]::Read,$true)
        if ($zip.Entries.Count -gt 20001) { throw 'Archive entry limit exceeded.' }
        $names = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
        $total = 0L
        foreach ($entry in $zip.Entries) {
            $null=EntryPath $entry.FullName
            if (-not $names.Add($entry.FullName.TrimEnd('/'))) { throw 'Duplicate archive entry.' }
            $mode = ($entry.ExternalAttributes -shr 16) -band 0xf000
            if ($mode -eq 0xa000 -or ($entry.ExternalAttributes -band 0x400)) { throw 'Archive symlink/reparse entry refused.' }
            if ($entry.FullName.EndsWith('/') -and $entry.Length -ne 0) { throw 'Nonempty archive directory entry refused.' }
            $total += $entry.Length
            if ($total -gt $limit) { throw 'Expanded archive exceeds size limit.' }
        }
        $manifestEntry = $zip.GetEntry($reserved)
        if (-not $manifestEntry -or $manifestEntry.Length -gt 8MB) { throw 'Missing or oversized manifest.' }
        $reader = [IO.StreamReader]::new($manifestEntry.Open())
        try { $manifest = $reader.ReadToEnd() | ConvertFrom-Json } finally { $reader.Dispose() }
        if ($manifest.version -ne 1) { throw 'Unsupported manifest version.' }
        $source = FullPath ([string]$manifest.source)
        if ((Within $target $source) -or (Within $source $target)) { throw 'Restore target overlaps source.' }
        if (Test-Path -LiteralPath $target) {
            if (-not (Test-Path -LiteralPath $target -PathType Container) -or @(Get-ChildItem -LiteralPath $target -Force).Count) { throw 'Restore target must be new and empty; overwrite refused.' }
        }
        $expected = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
        $null=$expected.Add($reserved)
        foreach ($record in $manifest.files) {
            $null=EntryPath ([string]$record.path)
            if (-not $expected.Add([string]$record.path)) { throw 'Duplicate manifest entry.' }
            $entry = $zip.GetEntry([string]$record.path)
            if (-not $entry -or $entry.Length -ne [long]$record.bytes) { throw 'Manifest length mismatch.' }
            $entryStream=$entry.Open()
            try { $digest=HashStream $entryStream $entry.Length } finally { $entryStream.Dispose() }
            if ($digest -cne [string]$record.sha256) { throw 'Manifest hash mismatch.' }
        }
        foreach ($name in $manifest.directories) { $null=EntryPath $name; if (-not $expected.Add($name.TrimEnd('/'))) { throw 'Duplicate manifest directory.' } }
        if (-not $expected.SetEquals($names)) { throw 'Archive entries differ from manifest.' }
        $fileNames = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
        foreach ($record in $manifest.files) { $null=$fileNames.Add($record.path) }
        foreach ($entry in $zip.Entries) {
            $parent = $entry.FullName.TrimEnd('/')
            while ($parent.Contains('/')) {
                $parent=$parent.Substring(0,$parent.LastIndexOf('/'))
                if ($fileNames.Contains($parent)) { throw 'Archive file/directory conflict.' }
            }
        }
        New-Item -ItemType Directory -Path $target -Force | Out-Null
        PrivateAcl $target
        foreach ($name in $manifest.directories) { New-Item -ItemType Directory -Path (Join-Path $target (EntryPath $name)) -Force | Out-Null }
        foreach ($record in $manifest.files) {
            $destination=Join-Path $target (EntryPath $record.path)
            New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
            $entryStream=$zip.GetEntry($record.path).Open(); $output=[IO.File]::Open($destination,'CreateNew','Write','None')
            try { $entryStream.CopyTo($output); $output.Flush($true) } finally { $entryStream.Dispose(); $output.Dispose() }
        }
        [pscustomobject]@{action='restore'; files=@($manifest.files).Count; verified_bytes=$total; scope='Windows CurrentUser DPAPI; same account/machine'} | ConvertTo-Json -Compress
    }
} finally {
    if ($zip) { $zip.Dispose() }
    foreach ($handle in $handles) { $handle.Dispose() }
    $memory.Dispose()
}
