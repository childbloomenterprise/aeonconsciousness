# Run AEON locally

2026-10-10 evidence and operating limits: see `AEON_RELEASE_2026_10_10.md`.

Windows, Node.js 24 or later, and the dedicated AEON Python installation are required.
Install enterprise dependencies once with `npm ci` inside `enterprise/`. The normal
worker reads only NVIDIA/Gemini credentials from the protected provider file created
by the enterprise installer. Its hosted connection and job state remain separate.

From the repository root:

```powershell
.\deployment\local-aeon.ps1 start
.\deployment\local-aeon.ps1 status
.\deployment\local-aeon.ps1 restart
.\deployment\local-aeon.ps1 stop
```

Open http://127.0.0.1:8787. Start builds the current source, checks Python/model
credentials/Chromium, starts the persistent local console, enrolls or reuses its
own local worker and starts the supervisor. No model request happens until a task
is queued. Submit a brief through the console, then inspect the result and download
artifacts. Restart applies source changes. Stop interrupts running jobs; inspect
their checkpoint before resuming tasks involving external actions.

Local private state defaults to `%LOCALAPPDATA%\AEON\localhost-private`:
`server/` contains SQLite and artifact objects; `worker/` contains the scoped
connection, jobs and checkpoints. Logs and the process registry live at the root.
State survives restart. Startup protects this directory with current-user access.
Process shutdown validates executable, command and creation time before stopping
the local process tree. The hosted service remains untouched.

For a console-only preview without model credentials:

```powershell
.\deployment\local-aeon.ps1 start -ConsoleOnly
```

This preview can create tasks but cannot execute them. To enable the worker, restart
without `-ConsoleOnly`. A different port/state directory supports isolated testing:

```powershell
.\deployment\local-aeon.ps1 start -Port 8788 -StateRoot "$env:LOCALAPPDATA\AEON\localhost-test" -ConsoleOnly
```

`AEON_LOCAL_STATE_DIR` and `AEON_LOCAL_PORT` also configure startup. Optional script
parameters select Python, Node, provider file and Chromium directory. Local worker
connections permit only an explicit HTTP localhost/127.0.0.1 origin. They cannot
reuse the hosted installation directory or Site credentials.

This is an owner-controlled development pilot with a fixed local identity,
not production authentication or an OS sandbox. The server binds loopback and
rejects foreign web origins/hosts. Generated work executes with the owner's host
permissions; only run trusted personal tasks. Model inference may use paid API
quota. The computer must stay awake while tasks execute.

## Encrypted stopped-state backup

Confirm no task executing, stop the launcher, then use an absolute archive path
outside repositories in an existing private directory. Backup refuses live
processes/listeners and does not stop them automatically:

```powershell
.\deployment\local-aeon.ps1 stop
.\deployment\local-state.ps1 -Action backup -ArchivePath "$env:LOCALAPPDATA\AEON\local-backups\snapshot.aeon-dpapi"
.\deployment\local-state.ps1 -Action restore -ArchivePath "$env:LOCALAPPDATA\AEON\local-backups\snapshot.aeon-dpapi" -RestoreRoot "$env:LOCALAPPDATA\AEON\local-backups\new-restore-drill"
.\deployment\local-aeon.ps1 start
```

The snapshot includes queue database, objects, worker identity, checkpoints,
ledger and memory. Restore accepts only a new empty destination, validates every
entry/hash, and never replaces original state. Never launch a restored worker
beside its original identity. DPAPI binds recovery to this Windows account and
machine; use a separately validated strategy for fresh-host or hosted recovery.
