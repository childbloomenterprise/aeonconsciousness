# SQLite backup strategy for owner-private AEON

This independently corrected report replaces unsafe advice in the original live-worker report. Original downloads and runtime status remain preserved. No backup or restore was executed for this correction.

| Method | Consistency and useful limits |
|---|---|
| Online Backup API | Copies through SQLite connections; successful completion yields a consistent database snapshot. Incremental steps release read locks between batches. Busy/locked handling and writes that restart copying need bounded retries. It uses fewer CPU cycles than VACUUM INTO. [SQLite Backup API](https://www.sqlite.org/backup.html) |
| VACUUM INTO | Creates a compact, logically equivalent snapshot without changing the source. Output must be absent or empty. It is not incremental; interruption can leave incomplete/corrupt output. With source synchronous NORMAL/FULL, SQLite syncs completed output. [VACUUM documentation](https://www.sqlite.org/lang_vacuum.html) |
| Raw live-file copying | A checkpoint alone does not freeze subsequent writes or coordinate copies of multiple files. Copying the main file while writers run, even followed by copying sidecars, does not establish a consistent backup. Committed changes may exist only in `-wal`; separating database/WAL can lose data or corrupt it. `-shm` holds the shared-memory WAL index, not a second durable transaction log. [WAL documentation](https://www.sqlite.org/wal.html) |

## Proposed whole-state procedure

Owner-provided AEON context: local SQLite metadata, artifact objects, original-worker identity and job checkpoints occupy separate parts of private local state. A database-only backup cannot restore all of them. Proposed procedure:

1. Pause submissions; reconcile consequential external effects separately. Stop the local server, worker supervisor and job children. Independently verify that no process/connection can mutate the chosen state tree during capture. Never treat one successful checkpoint as that verification.
2. Capture the complete stopped local-state tree: database and any retained WAL/sidecars, artifact objects, worker identity/connection, job workspaces/checkpoints, ledgers and associated memory. Do not delete WAL manually. Inventory sizes and SHA-256 hashes; keep a recoverable, protected manifest.
3. Encrypt/archive outside the repository with restrictive access. Inventory external dependencies separately: provider credentials, browser/runtime versions and installation requirements are not guaranteed to live in the local-state tree. Preserve or securely re-provision them without publishing secrets.
4. Restore into a separate protected destination. Verify every manifest hash, SQLite integrity/foreign keys, task-to-artifact associations, downloads and worker/checkpoint identity. Exercise interrupted recovery using harmless fixtures; do not blindly replay external effects. Keep the original state available for rollback.

An online database snapshot is another valid database capture method, but coordinating it with changing artifact/checkpoint files remains an application-level requirement.

The DPAPI local-state utility is under development; this report does not claim its implementation or restore acceptance. Its intended same-Windows-account/machine protection is not a tested new-machine disaster-recovery solution.

Restart persistence retains existing storage. Disaster recovery additionally needs an independently tested restore from protected backups, including machine-loss/key recovery and agreed recovery objectives. Those gates remain open.
