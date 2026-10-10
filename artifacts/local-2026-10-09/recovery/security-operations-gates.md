# Enterprise security and operations gates — 2026-10-09

Source inspection: current `aeon_enterprise/`, `enterprise/worker/`, `enterprise/scripts/`, `deployment/`, and `docs/AEON_ENTERPRISE_OPERATIONS.md`. Assessment covers this checkout, not deployment parity or certification. No hosted identity, real secret, user queue, or production state was modified for this audit.

Current boundary: owner-private pilot; trusted-local jobs retain the worker account's host permissions. Application grants and localhost request guards do not provide an operating-system sandbox. Passing 28 Node tests and 11 focused Python recovery tests covers the recorded fixtures only.

## Gate checklist

| Gate | Existing evidence / implementation | Concrete remaining acceptance | Status |
|---|---|---|---|
| Production/local boundary | Build entry is `enterprise/worker/index.js`; development D1/R2 adapters live separately in scripts | Inspect release bundle/imports for development server, SQLite adapter, fixed local owner, private paths and credentials; prove localhost adapter unreachable in published production; verify installed wheel and hosted source revision | Open live parity |
| Untrusted task isolation | Docker command specifies non-root image user, read-only root, dropped capabilities, no-new-privileges and resource limits; no Docker socket mount | Actually build/run on supported host; adversarial attempts to read host/other-job files, escape mounts, exhaust resources and leave child processes; verify browser sandbox and process teardown | Open; Docker execution not verified here |
| Egress policy | Tool-level URL/domain guards; normal container networking | Enforce/test network boundary against private/LAN/metadata addresses, redirects/DNS changes and unauthorized outbound effects; provider/web allowlist with observable denied requests | Open; no egress proxy inspected |
| Provider credentials | Supervisor omits worker/admin/Sites credentials from task execution environment; model credentials supplied to runtime | Key proxy/vault scoped by tenant/job, rotation and revocation drills, secret redaction tests across traces/artifacts/commands, isolation from generated code and compromised worker | Open |
| Customer identity and access | Hosting authentication, organization/role checks, owner bootstrap, email-bound invitations and scoped worker tokens; tested tenant hiding and revocation | Customer SAML/OIDC and SCIM/deprovisioning; independent multi-tenant test identities on actual deployment; denied worker attempts at approvals/team APIs; simultaneous role-revocation exercise | Open customer rollout |
| Authority and consequential effects | Approval, explicit owner override, named actions/domains/recipients; spending disabled; stale/cancelled leases rejected | Controlled fake effect sink verifies allowed action, blocked action, cancellation, reconnect and repeated claim semantics; duplicate external-effect protection or explicit recovery requiring reconciliation | Open exactly-once effect behavior |
| Limits and queue state | Atomic quotas/claims; cancellations retain reservation; cumulative cap repair now rejects overflow; tests include exact runtime caps | Load-test simultaneous resumes near all caps; actual provider usage/cost reconciliation; zero-evidence and unfinished checks cannot produce completion; monitor stranded jobs | Fixture pass; load/billing open |
| Recovery and cancellation | Real isolated HTTP provider outage/restart/resume/artifact flow; hard-exit and terminal-write fault injection; original-worker recovery | Actual supervisor/worker termination at each checkpoint window, Windows child-tree cancellation, expired leases after reboot, unavailable provider retry policy, restored identity/checkpoint pairing | Deterministic and fault fixtures pass; host drills open |
| Backup and restore | Organization JSON export and downloadable artifact bundles; SQLite local persistence; individual writes/checkpoints atomic | Complete database + artifact objects + worker checkpoints, ledger, approved memory and identity inventory; encrypted backups; fresh-host restore drill; every artifact hash and tenant association verified; explicit RPO/RTO | Open; no backup/restore implementation found |
| Retention and deletion | Export exists; artifact records/object storage persist | Tenant retention policy, authorized deletion/legal-hold semantics, object cleanup including unreferenced uploads, worker logs/checkpoints/memory and backup expiry; repeatable deletion evidence | Open; no tenant retention/deletion workflow found |
| Audit integrity | Runtime hash-chain audit; API appends control-plane events | External anchoring/signature or independent audit store where required; restoration continuity and tamper tests; access, retention and export controls | Open stronger assurance |
| Dependency/release security | Third-party notices, CI checks and release tooling exist | Current dependency audit, reproducible source/wheel/bundle manifests, exact deployed revision, independent security review and tracked findings closure | Open until release evidence recorded |
| Capacity and operations | Health endpoint, logs, heartbeat/lease and explicit interrupted state | Real queue/worker/artifact load thresholds; latency/error/queue-age/worker-offline metrics; alert delivery, on-call runbook, failure drill and SLO/error-budget ownership | Open |
| Quality and superiority | Matched paired harness, opaque review packs and paired confidence gates | At least 30 genuinely unseen paired briefs after source freeze, matched effective models/tools/budgets, locked independent blind grading and factual/interaction checks | Open; superiority unproven |

## Backup implementation finding

No dedicated backup, restore, retention or tenant-data-deletion script/API was found in the inspected runtime/deployment directories. `/orgs/:orgId/export` exports records and artifact metadata, not the R2 object bytes or worker checkpoints. Artifact downloads/bundles do not include a full database/worker-state restore procedure. Server restart persistence therefore cannot be reported as disaster-recovery acceptance.

Required backup set spans two state owners: control-plane database/object store and original worker identity/checkpoints/ledger/qualified memory. Restoring only task records cannot resume jobs that remain bound to an original worker; creating a replacement identity does not supply its checkpoint. Store credentials separately from publishable evidence and test revocation/rotation after restoration. A local SQLite WAL database requires a consistent backup method or controlled shutdown; copying only its main file while writes continue does not establish a coherent snapshot.

## Independent review of current recovery changes

- Ceiling reconciliation uses cumulative control-plane limits, preserves unchanged replay deadlines and applies a new explicit extension once; tests cover all four budget fields and second extensions.
- Running-to-interrupted conversion occurs under `run.lock`; serialized supervisor ownership and the OS-backed lock make orphan recovery safe for supported entry points.
- Terminal `final_result` is now saved in the same atomic checkpoint as terminal status. Reads use that payload before legacy result files, covering both absent and stale result-write crash windows for newly finalized tasks.
- Resume grants do not broaden action domains, recipients or external-action authority. Existing task grant remains checkpointed; approval is still control-plane-owned.
- Atomic cumulative API guards match runtime limits: 200 steps, 20 revisions, 1,440 minutes, and organization token ceiling. Newly added HTTP test confirms overflow does not mutate task/audit.
- Legacy terminal checkpoints lacking both embedded final results and result files still require explicit repair; the new finalization path cannot retroactively create missing historic evidence.

No certification, general enterprise readiness, proven superiority, or exactly-once external-effect guarantee follows from these changes.
