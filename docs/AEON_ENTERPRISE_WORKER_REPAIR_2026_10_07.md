# AEON Enterprise — worker recovery, 7 October 2026

Live console: https://aeon-enterprise.childbloomenterprise.chatgpt.site

GitHub: https://github.com/childbloomenterprise/aeonconsciousness

## Failure and repair

The owner-private Windows worker stopped because its checkout virtual environment
referenced a Python installation managed by another tool; that installation disappeared.
The hosted control plane stayed available, but queued work could not execute.

The worker now runs from a dedicated Python 3.11.15 installation, virtual environment,
installed AEON wheel and Chromium under `%LOCALAPPDATA%\AEON\enterprise-private`.
The installed `aeon_enterprise.service` module loads model credentials from protected
configuration and launches the existing supervisor. Startup no longer imports scripts
from the checkout or relies on the other tool's Python cache.

Windows startup performs an installation check before spawning a hidden process,
checks for immediate failure, and uses a protected copy of its launcher. Installation
rejects upgrades while that supervisor runs. The existing enrolled worker identity,
credentials and job checkpoints were preserved. Current-user login startup was updated;
an actual Windows logout/reboot was not performed.

The first repair assignment produced correct files but skipped the requested local
arithmetic command. Its runtime returned completed, and initial file acceptance passed;
inspection of the tool ledger exposed missing execution evidence. That process
acceptance is now marked failed and superseded. The completion gate now requires a
successful execution receipt tied to current artifact contents when local verification
is requested. Changed artifacts invalidate prior receipts; zero discovered Python tests
and syntax compilation do not satisfy the requirement. Receipts persist through resume.

## Verification evidence

| Check | Result |
|---|---|
| Root regression suite | 186 run: 184 passed, 2 optional NVIDIA toolkit skips |
| New service/startup regression tests | 5 passed |
| Command evidence regression tests | 5 passed: missing/stale checks, real script, resume, zero tests and explanation-only briefs |
| Dedicated installer | Completed without administrator privileges |
| Broken interpreter startup | Rejected before background launch |
| Installed module launched outside checkout | Running; hosted worker heartbeat observed |
| Running supervisor upgrade | Rejected before package replacement |
| Protected installation permissions | Current Windows user full control; inheritance disabled |
| Hosted health | Ready, D1/R2 available |
| Evidence-gated live rerun | Completed in 29 seconds; Gemini `gemini-3.5-flash-lite`; 13,946 tokens |
| Downloaded artifacts | All 5 SHA-256 hashes match hosted metadata |
| Independent source-row/arithmetic check | 3 original rows, quantity 9, total USD 76.50 |
| Runtime result | Ledger independently rechecked, current-artifact command receipt, no gaps, original worker |
| Autonomous recovery | Unsupported check failed; agent wrote an assertion script and ran `python_script` successfully |
| Previous GitHub release CI | [Passed on commit 4d2246f](https://github.com/childbloomenterprise/aeonconsciousness/actions/runs/37185231466) |

Verified rerun: `job_991f84f1c4d643b780a0f549e81f7979`.

Superseded file-only acceptance: `job_8d2663b30d274fb19ce011b09dde14d2`.

Artifacts: `worker-acceptance.json`, `worker-acceptance.md`,
`verify_calc.py`, `evidence/runtime-result.json`, `deliverables.zip`.

Local evidence: `artifacts/enterprise-0.4.0/2026-10-07-evidence-gate/live-acceptance.json`
and `ledger-check.json`. Initial repair CI exposed a test assertion comparing Windows
short and resolved long temporary paths; the assertion now normalizes paths.
The repeatable acceptance helper uses an idempotency key and does not enroll or replace
workers. This is another real task demonstration, not a comparative success-rate study.

## Use and remaining boundaries

Follow [operations guide](AEON_ENTERPRISE_OPERATIONS.md) for installation and authority.
The site remains an owner-private pilot. Browser sign-in acceptance was deferred by the
owner; authenticated API/worker/artifact acceptance passed. Desktop/mobile UI checks
recorded in the original release used a local harness, not a signed-in production browser.

The computer must remain awake and online for this local worker. The hosted console
and queue remain available when it sleeps. Trusted-local mode retains host account
permissions. Docker execution, customer SSO/SCIM, provider-key isolation, load testing,
retention, backup restore and operational SLOs remain rollout gates. Consciousness and
superiority over a normal agent are unproven.

Hosted Worker code and database migration were unchanged by this maintenance repair;
the deployed Site still uses source commit `a89f3e7fccd7473793c2ef430f3015b92d2d3bd2`.
