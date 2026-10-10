# Independent artifact correction — 2026-10-10

Original live-worker downloads, statuses and evidence remain unchanged. Only this `corrected/` directory contains revisions.

- `backup-strategy.md`: replaces checkpoint-only copying advice with coordinated SQLite snapshots or a verified stopped whole-state capture; distinguishes WAL committed data from the shared-memory index; includes separate artifact/checkpoint/identity preservation, hash checks and isolated restore acceptance. Utility status explicitly remains under development; no backup execution or disaster-recovery claim.
- `source-summary.json` and `checked-summary.md`: supported SQLite claims paraphrased and cited; provenance states that original worker omitted the required assertion check.
- Actual independent check: bounded 10-second process returned 0 in less than one second. Original and corrected JSON parsing/fields/title/URL/three-string assertions passed; Markdown citations present; all seven original downloaded sizes/hashes still match recorded metadata. This is a post-completion acceptance check, not a worker receipt.
- Primary-source review: [Backup API](https://www.sqlite.org/backup.html), [VACUUM INTO](https://www.sqlite.org/lang_vacuum.html), [WAL](https://www.sqlite.org/wal.html) and [About SQLite](https://www.sqlite.org/about.html), inspected directly from official SQLite documentation.

`assertion-receipt.json` records execution, `corrected-hashes.json` fixes corrected artifact SHA-256 hashes. Content review supports the corrected research/browser deliverables; original worker's missed execution requirement remains a historical defect. No live jobs, resumes, external messages, deployments or user-state mutations were performed for these corrections.

## Owner-private release recommendation

The operations document places SSO/SCIM, validated untrusted-tenant isolation/egress, key proxy, retention, restore drills, independent security review, load/SLO monitoring and superiority evidence before broad enterprise rollout. Those open rollout gates do not automatically prohibit a verified update to the existing owner-private pilot.

Proceed with a pilot update only after relevant regressions/build checks and actual published behavior pass, keeping existing private access/authority restrictions and accurate capability labels. Never publish the localhost HTTP adapter, fixed development owner, provider credentials or private worker state. Do not expand to untrusted tenants or claim enterprise launch/certification, complete disaster recovery, exactly-once effects or superiority while their gates remain open.

Recommendation concerns release scope; it does not assert that pending code, DPAPI utility or a future deployment has passed verification.
