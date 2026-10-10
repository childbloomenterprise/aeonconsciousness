# Two live local demos — 2026-10-10

Exactly two fresh tasks submitted with saved stable idempotency keys. Existing original-worker supervisor executed both with real Gemini `gemini-3.5-flash-lite`; NVIDIA fallback recorded because its key was absent. No deterministic adapter, automatic resume, extra task, external modification, or superiority claim.

| Demo | Saved job | Runtime result | Recorded usage | Independent acceptance |
|---|---|---|---|---|
| SQLite backup research | `job_0a6b835ae774473a8ec703b7c946b862` | completed, valid audit reported | 16,913 tokens; 4 steps; 21.32s | Needs correction |
| SQLite browser/file | `job_e58d2d252c72405e9a600e2a0a736808` | completed, valid audit reported | 11,451 tokens; 3 steps; 14.81s | Content passes; required worker execution missing |

Independent download checks passed for every artifact: 3 research artifacts and 4 browser/file artifacts. Sizes/SHA-256 matched API metadata; responses used attachment headers. Both ZIP bundles passed CRC checks, and every member equaled its independently downloaded individual artifact. Inspector JSON assertions also passed: required fields, exact title/source URL, exactly three nonempty strings, cited Markdown and factual limits. These inspector checks are not worker execution receipts.

## Research report defects

Downloaded `backup-strategy.md` says: “Avoid raw live file copies unless the database is quiesced or checkpointed and accompanied by its WAL state.” Checkpointing plus copying sidecars alone does not establish a coordinated snapshot when writers continue. Recommendation must require a consistent snapshot/lock or a controlled stop, or use the backup API/VACUUM INTO successfully. SQLite explains that committed state can reside in WAL and must remain coordinated with its database. [Official WAL documentation](https://www.sqlite.org/wal.html).

Report also describes “missing active transactions in the WAL (`-wal`) and shared-memory (`-shm`) files”. This conflates durable transaction state with the shared-memory WAL index and fails to distinguish committed data from active uncommitted transactions. The WAL index supports lookup; WAL holds the committed changes absent from the main database. [Official WAL documentation](https://www.sqlite.org/wal.html).

Report acknowledges separate artifact objects/worker identity/checkpoints, but its proposed backup/restore steps cover only the database snapshot and initialization/integrity check. It does not specify preserving those separate resources or testing object hashes, task associations and original-worker recovery. This is an incomplete AEON backup strategy, not evidence of implemented disaster recovery. Basic API/VACUUM comparisons are supported by [SQLite Backup API](https://www.sqlite.org/backup.html) and [VACUUM documentation](https://www.sqlite.org/lang_vacuum.html); relevant limitations such as interrupted VACUUM output and incremental backup retries are omitted.

## Browser/file acceptance defect

All three JSON claims are supported by the independently inspected [About SQLite page](https://www.sqlite.org/about.html). Recorded source evidence uses that exact URL; no additional inspected source appears. Worker output correctly avoids empirical performance/certification claims.

However, the brief explicitly required a real bounded local assertion check, and the work order repeated that hard requirement. Runtime records only browser navigation, JSON write and Markdown write; `command_checks` is empty. Runtime `completed` therefore overstates fulfillment of the full brief. Independent inspector assertions verify the delivered files but cannot retroactively satisfy the worker's missing execution requirement. Parent was notified for a completion-gate regression/fix before publication.

Evidence: `requests.json`, each demo's `submission.json` and `control-plane-result.json`, `download-checks.json`, original downloads, and `independent-acceptance.json`. Token counts are reported usage, not reconciled charges. These two individual demos do not establish general reliability or superiority.
