# Handoff — AEON paired benchmark state (as of 2026-10-10, for continuing work from another assistant/GPT)

Follow-up: source/citation policy repaired and two unchanged-brief replays completed; independent checks 13/14. Checkpoints correct the proposed delivery-phase cause: pricing writes were source-gated; `delivering` was later upload status. Original results below preserved. See [current release/evidence](../../docs/AEON_RELEASE_2026_10_10.md).

## What this workstream is

A paired live-model benchmark inside the AEON repo answering one question:
**does wrapping the same model in the AEON framework (planning, verification, audit)
improve outcomes vs. just prompting the model directly — and at what cost?**
Both arms use the SAME model: `gemini-3-5-flash-lite` (framework arm rides the
enterprise control plane; standalone arm calls GenerateContent directly with a
minimal system line + JSON schema hint).

Everything lives in `artifacts/paired-lean-benchmark-2026-10-10/`:

| File | What it is |
|---|---|
| `REPORT.md` | readable report, lean round-2 section + complex round-3 section + honest caveats |
| `usage-round2.json`, `usage-round3.json` | per-task/per-arm token + status evidence |
| `verification-round2.json`, `verification-round3.json` | per-check objective scores |
| `run_framework_arm.py` (+`_r3`), `run_standalone_arm.py` (+`_r3`) | idempotent drivers (submit/poll) |
| `briefs.json`, `briefs-complex-round3.json` | task suites with acceptance criteria |
| `verify_artifacts.py`, `verify_round3.py` | objective verifiers |
| `complex-*/`, `standalone-complex/*`, `*-r1`, `*-killed` folders | raw artifacts per task per arm |

## Completed so far (verifiable, on disk)

### Round 2 — lean "caveman" tasks (single-pass: research file, portfolio site, user-understanding doc)
- Framework: 44,079 tokens, 1/3 clean completions, 12/15 checks. Standalone: 3,323 tokens, 3/3 completions, 15/15 (~13× cheaper).
- **Real bug found & fixed in the framework:** `aeon_worker/runner.py` `_call` preflight
  estimated input tokens as `chars//2` (~2.4× overestimate measured against the real
  `countTokens` API); changed to `chars//4 + 512` at [aeon_worker/runner.py:383](../../aeon_worker/runner.py).
  Verified with `tests.test_aeon_worker` → 79/79 OK (~117 s).
- Round-1 folders (`*-r1`) retained as pre-fix evidence.

### Round 3 — complex, high-comprehension tasks (deliberately incomplete/ambiguous inputs)
Suite in `briefs-complex-round3.json`, 3 tasks; goal: test the hypothesis that the
framework makes the agent "think on itself" when inputs are under-specified.
1. **complex-brief-underfill** — pricing-page email with 7 missing facts; must enumerate gaps, choose safe/reversible defaults, name what cannot be built without answers.
2. **complex-conflicting-constraints** — status dashboard with an *intentionally unknown* feed schema: `normalizeFeed` + TODO schema questions + on-page Known Limitations + working offline fallback (also requiring a self-run browser test to exercise the fallback path).
3. **complex-user-intent-truncated** — support message cut off mid-sentence; must separate facts vs inferences with high/medium/low confidence, list ≥4 unknowables, reply without promising a deadline or asserting a cause.

Results (same model both arms; all numbers machine-checked + manually read):
| Task | Framework | Standalone |
|---|---|---|
| underfill | failed, 18,023 tok, deadline at delivering with NO file emitted → 0/7 | 854 tok → 7/7 |
| constraints | partial, 27,412 tok, good `status.html` + desktop/mobile screenshots → 7/7 | 2,796 tok → 7/7 |
| truncated | partial, 19,019 tok → 7/7 content checks; `partial` only because AEON's own gate false-flagged "missing citations" on a no-research brief | 822 tok → 6/7 (2 words over its own 350 limit) |

Totals: **framework 64,454 tok → 14/21, 0/3 clean; standalone 4,472 tok → 20/21, 3/3 (~14.4× cheaper)**.
Hypothesis did NOT hold in the favorable direction at this scale; framework overhead *grew* with complexity.

### Defects found in the framework (documented with evidence, not yet fixed)
1. Budget/deadline/step guards fire **at the `delivering` phase** after the deliverable is essentially done (2/3 complex tasks). Round-2's preflight fix handles the input estimate but output-heavy deliverables still race the guards.
2. Verification policy false positive: briefs that forbid outreach/research get flagged "does not cite a source URL" as an `error` finding (visible in `complex-user-intent-truncated/downloads/evidence/runtime-result.json` → `unresolved_gaps`).
3. The FEED_URL "multiple definitions" was adjudicated a PASS after evidence review: the extra sites are the deliverable's own offline-failure test harness (`status.html` lines 257–261); single config definition at line 171. Adjudication text is embedded in `verification-round3.json`.

### Infra/ops notes (needed to reproduce)
- Local stack: `powershell -File deployment/local-aeon.ps1 -Action restart` (server+worker on `http://127.0.0.1:8787`, state at `%LOCALAPPDATA%\AEON\localhost-private`). It dies with the host session — restart and re-poll; jobs in flight get killed mid-execute.
- Infra-killed jobs get retried on a **fresh idempotency key** (`-retry1` suffix in `run_framework_arm_r3.py`), brief unchanged. One truncated run was killed this way at 15,069 tok; that's infra cost, not model/framework cost.
- Control-plane `used_tokens` can show 0 while a job runs; live progress is in `%LOCALAPPDATA%\AEON\localhost-private\worker\jobs\<job>\state\.../checkpoint.json`.
- Standalone arm reads the Gemini key from `%LOCALAPPDATA%\AEON\enterprise-private\providers.json`.

### Verification status
- Cross-file consistency proven programmatically: `verification-round3.json`, `usage-round3.json`, `REPORT.md` totals reconcile (zero mismatches; final pass script asserted 14/21, 20/21, 64,454, 4,472, 14.4 all present).
- Framework jobs carry `audit_valid: true` + SHA-256-verified artifact downloads on all tasks.
- Repo test suite untouched by round 3 (only `artifacts/` drivers added; the round-2 `runner.py` fix has tests passing 79/79).

## Honest limits (carry these forward)
- **Exploratory: 3 tasks × 1 seed per arm**, single model, no ordering control. The repo's own standard (`docs/AEON_PYRAMID_ARCHITECTURE_AND_VALIDATION_2026-09-27.md`, employee-autonomy blueprint) sets 30-pair matched-baseline gates before any superiority claim — do NOT claim one from this data.
- One manual adjudication exists (FEED_URL); it's documented with line evidence, re-checkable.
- Framework token totals include its verification loops/screenshots; cost-per-final-quality comparisons at this scale are indicators, not proof.

## Open next steps (ranked, from last user-driven session)
1. **Fix AEON defect A:** deliver-phase guard firing after deliverable completion (retry/budget race) + `aeon_worker` test.
2. **Fix AEON defect B:** citation/source policy check must not mis-fire on briefs that forbid research (pass brief constraints into the verification gate).
3. **Multi-seed reroll** of the complex suite (e.g., 3 seeds × 3 tasks × both arms) to check stability of the 14.4× gap.
4. **Round-4 class where framework machinery should pay off**: long-horizon tasks with interruption/resume, injected tool failures, mid-task revised requirements — this is the dimension that would actually falsify/support the "framework makes the agent think" hypothesis.
5. Optionally port lean/complex suites into `agent_lab/paired_benchmark.py`-style harness if continuing as a permanent regression benchmark.
