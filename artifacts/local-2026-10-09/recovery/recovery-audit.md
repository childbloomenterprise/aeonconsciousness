# Isolated recovery audit — 2026-10-09

Scope: current working tree. All new fixtures use temporary state, loopback ports allocated by the OS, deterministic callback adapters, and no model credentials. No genuine localhost:8787 queue or hosted service was accessed by this audit. No production or Docker-runtime acceptance claim.

## Demonstrated defects and repairs

1. Replaying a resumed job reapplied the saved relative token extension: checkpoint 22,000 tokens vs authorized queue ceiling 21,000. Parent repaired `aeon_enterprise/execute.py` to reconcile cumulative queue ceilings with saved checkpoint limits. New regression checks token/step/revision/minute ceilings and unchanged deadline on identical replay; a second explicit extension still applies.
2. Replaying locally completed resumed work raised `ValueError: Budget extension requires a partial or interrupted task`. Parent repaired terminal-checkpoint execution to reuse completed results without invoking a provider or applying stale extensions.
3. Provider failure before planning followed by a budget extension resumed into execution without a work order, producing failure. Parent repaired `TaskRunner.resume` to return to planning when no work order exists. New regression completes after pre-plan outage recovery.
4. Abrupt process exit left a running checkpoint; extension recovery rejected that status. Under the exclusive run lock, parent now recognizes that saved running state as orphaned/interrupted before applying explicit limits. Fault-injection regression passes.
5. Terminal checkpoint saved before its result file could survive with a missing/stale interrupted result. Parent now saves terminal status and its matching `final_result` in one atomic checkpoint; result reads prefer that authoritative payload. Fault injection retains a stale interrupted `result.json` and verifies completed replay without a provider call.
6. Control-plane cumulative resumes could exceed the runtime's total step/revision/minute caps. Parent now rejects overflow upfront and checks caps in the atomic mutation. HTTP regression verifies rejected overflow leaves both task and audit unchanged and accepts exact caps: 200 steps, 20 revisions, 1,440 minutes.

## Verification

| Check | Result | Evidence |
|---|---|---|
| Local Python service/recovery suite | 11 passed, 0 skipped | `python-local-service.log` |
| Entire Node API/local HTTP suite | 28 passed | `node-enterprise.log` |
| Real isolated HTTP task flow | Queue → claim → deterministic file generation → provider failure → checkpoint and partial artifacts → server restart → same enrollment → explicit resume → completion → upload → second restart → every downloaded SHA-256 matches | Python recovery suite |
| Terminal replay | Saved completed result; provider callback cannot execute | Python recovery suite |
| Cancellation | Old heartbeat/upload/finish rejected; cancelled resume rejected; token reservation retained; job no longer claimable | Node HTTP suite |
| Lease expiry | Interrupts task; explicit resume; original worker only; new lease invalidates old authority | Node HTTP suite |
| Role and request boundaries | Tenant hiding, scoped worker identity, approval, body bounds, quotas, traversal, revoked workers, Host/Origin/Fetch-Site validation | Existing Node regressions plus new HTTP cases |

Tests added only in `tests/test_local_enterprise_service.py` and `enterprise/tests/local-server.test.mjs`; runtime repairs owned by parent. Existing tests retained. Fixture state removed during cleanup.

## Practical limits

- Deterministic recovery proves orchestration and persistence behavior, not model-task quality or live-provider reliability.
- Cancellation checks control-plane revocation. Existing supervisor logic stops processes on rejected heartbeat; actual process-tree termination under Windows and external-effect cancellation remains a separate acceptance exercise.
- HTTP persistence is restart recovery, not a verified database backup/restore or disaster-recovery plan.
- Docker isolation/egress, customer SSO/SCIM, key vault/proxy, retention/deletion, independent security review, production load/monitoring/SLOs remain open as recorded in operations docs.
- Current staged/source changes do not establish published or deployed parity.

## Superiority gate

Current harness can execute matched direct/AEON pairs, freeze effective provider route, record case/source digests and usage, preserve provider-retry attempts, create opaque artifact review packs, and calculate paired confidence gates. It rejects mismatched routes and provider-interrupted pairs for claim analysis.

Neither checked-in 30-case suite qualifies as unseen. `docs/AEON_WORKER_ACCEPTANCE_STATUS.md` explicitly records execution, recovery, grading, and development informed by the `holdout-30-v2` cases. A new name or output directory does not restore their unseen status.

Required before honest superiority claim: frozen implementation and matched tools/model/budgets; independently supplied unseen briefs (at least 30 valid pairs); locked blind grades with grader provenance; runtime interaction/factual checks beyond static excerpts; zero unauthorized completed effects; success gain at least 10 percentage points with positive lower paired confidence bound. Current evaluator also imposes score/safety/cost gates. Automated two-pass reviewer exists, but its documented limits include static interaction review, source sampling, model bias, and unverified independence for user-supplied ratings.

No live comparison or fabricated ratings were generated. Prior comparison did not pass; current-source superiority remains **unproven**.
