# Paired Live Benchmark — AEON Framework vs Standalone Agent (Lean "Caveman" Mode)

> **Handoff:** for the full state snapshot, defects list, and next steps, see [HANDOFF.md](HANDOFF.md).

**Date:** 2026-10-10
**Model route (both arms):** Gemini `gemini-3.5-flash-lite` (framework arm via AEON enterprise provider credential; standalone arm via the same key calling the GenerateContent API directly). Framework arm provider shows its normal NVIDIA→Gemini failover record because no NVIDIA key is configured on this machine.

**Design:** Three tasks (research, website-from-XYZ-prompt, user-understanding) run in two conditions with the SAME model and same briefs:
1. **Framework arm:** full AEON worker (`aeon_enterprise.local_service` + local control plane) with subgoals, checkpoints, verification, browser access, budget guardrails, hash-chained audit.
2. **Standalone arm:** no framework — a single raw chat-completions call with a minimal "caveman" system wrapper and a JSON output schema hint.

**Round used for scoring:** round 2 (framework arm fixes one bug: `_call` preflight overestimated input tokens (`chars//2` instead of `chars//4`), which prematurely aborted tasks near the budget; fix verified by `tests.test_aeon_worker` 79/79 OK).

---

## Live result (round 2, same model)

| Task | Arm | Status | Model tokens | Elapsed | Deliverables | Acceptance checks |
|---|---|---|---:|---:|---|---|
| Research UX checklist | Framework | partial (`model_token_budget`) | 17,404 | 25.9s | ux-checklist.md | **4/4 objective checks passed** |
| Research UX checklist | Standalone | completed | **802** | 3.0s | ux-checklist.md | **4/4 objective checks passed** |
| Website portfolio | Framework | partial (`model_finished`) | 17,149 | 69.5s | index.html + **desktop.png + mobile.png** (visual evidence) | **6/6 checks passed** |
| Website portfolio | Standalone | completed | **2,197** | 5.1s | index.html | **6/6 checks passed** |
| Understand user | Framework | partial (`model_token_budget`) | 9,526 | 14.9s | answer.md (blocked note, not the deliverable) | **2/5 checks passed** |
| Understand user | Standalone | completed | **324** | 1.5s | user-understanding.md | **5/5 checks passed** |

Totals (same model): **framework 44,079 tokens for 1 of 3 clean completions; standalone 3,323 tokens for 3 of 3 completions**, delivering all nine objective acceptance checks across tasks. That is a **~13× token advantage to the standalone arm** on these tasks. Framework arm ran with `audit_valid: true` in every runtime result (tamper-evident chains intact).

Research output quality (framework = 4/4 checks): the framework deliverable was a properly cited 8-item checklist (176 words, all citations to nngroup.com, matching briefs). Standalone output similarly 4/4 (209 words, same citation discipline). Both verified by machine checks in `verification-round2.json`.

---

## Round-1 (pre-fix) context, kept for honesty

Round 1 (before the `_call` preflight fix) also recorded larger-than-necessary overheads:
framework used 11,510/17,404/7,344 tasks tokens (research/website/user) with 0/1/0 deliverables respectively,
standalone used 596/1,994, with the user-task returning no file until the round-2 schema hint was added. Both fixes (preflight formula AND the schema hint for JSON return shape) are documented here as a lesson: **a framework's budget heuristics can themselves waste budget, and a one-line output schema hint measurably saves calls.**

## Metrics files

- `usage-round2.json` — per-task, per-arm token & elapsed & status data (live Gemini usage counters).
- `verification-round2.json` — per-check pass/fail objective scores for both arms.
- `run_framework_arm.py`, `run_standalone_arm.py` — the two arms' drivers, idempotent (saved idempotency keys v2).
- `control-plane-result.json` per task — full framework job record; `standalone/*/result.json` — standalone records.
- All artifacts downloaded with SHA-256 + size verified through the artifacts API.

## Caveats

- Exploratory pilot; sample = 3 tasks × 1 seed per arm (plus a pre-fix round 1). Same model and same prompt; no ordering control, no multiple seeds.
- Framework wall-time includes browser visual review screenshots and multi-step verification loops; standalone elapsed reflects single forward pass.
- `model_finished` partial for website in the framework arm: the worker delivered the site and screenshot artifacts but ended in `partial` because its brief asked for no external research, which the AEON gate recorded as an unfilled source requirement (a policy interplay, not a product defect; future briefs should either allow or cleanly disallow research phrasing).
- Cost-effective "caveman" prompt effect measured within the framework via round-1 vs round-2 usage deltas and in standalone vs framework token gaps; not a full factorial experiment.

## What this demonstrates (and does not)

- Demonstrates: deterministic coordination overhead of a full framework (planning, verification, budget guardrails, screenshots, audit) vs raw single-pass generation on lean, self-contained tasks. On cost, the lean single-pass wins decisively on these three tasks.
- Does not demonstrate: advantage on long-horizon, ambiguous, or tool-heavy tasks where the framework's verification and recovery loops typically pay off (that requires a matched-baseline protocol with adversarial variants, as the repo's earlier pilot did).

---

# Round 3 — COMPLEX comprehension tasks (incomplete / ambiguous inputs)

**Files:** `briefs-complex-round3.json` (suite), `run_framework_arm_r3.py`, `run_standalone_arm_r3.py` (drivers), `verify_round3.py` (objective verifier), `verification-round3.json`, `usage-round3.json`.

**Purpose of this round:** test the hypothesis that complex tasks requiring "more understanding" change the comparison. Three briefs with deliberately missing information, conflicting soft constraints, and a truncated user message:
1. **complex-brief-underfill** — a pricing-page request with 7 information gaps; the deliverable must identify the gaps, pick safe/reversible defaults, and name what must not be built without answers.
2. **complex-conflicting-constraints** — a status dashboard requiring a feed adapter whose schema is *unknown by design*; the deliverable must ship a `normalizeFeed` with documented TODO schema questions plus an on-page Known Limitations section, and prove the offline fallback works.
3. **complex-user-intent-truncated** — a support message cut off mid-sentence; the deliverable must separate stated needs from inferences with confidence labels, list what cannot be known, and send an empathetic reply that never promises a fix deadline or asserts a cause.

## Round-3 results (same model, `gemini-3.5-flash-lite`)

| Task | Framework arm | Standalone arm |
|---|---|---|
| pricing brief with gaps | **failed** — 18,023 tok, 6 steps, hit **deadline** at `delivering` with **no required file emitted**; 0/7 acceptance | **completed** in 854 tok — 7/7 after adjudication (~21× less than framework; framework delivered nothing) |
| conflicting constraints dashboard | **partial** — 27,412 tok (`model_token_budget` at delivering), but produced `status.html` + desktop/mobile screenshots; **7/7** after adjudication | **completed** in 2,796 tok — **7/7** (9.8× less) |
| truncated user message | **partial** — 19,019 tok, deliverable in `deliverables.zip`; **7/7 content checks pass**; ended `partial` only because its own run-finding "does not cite a source URL" is a **false positive of AEON's policy gate** (brief forbids browsing/citations) | **completed** in 822 tok — **6/7** (loses only its own 352-vs-350 word limit, ~2 words over) (23× less) |

Totals: framework **64,454 tokens → 14/21 acceptance checks, 0/3 clean completions** (1 failed-empty, 2 partial); standalone **4,472 tokens → 20/21, 3/3 completed** (~14.4× cheaper). All framework tasks carried `audit_valid: true` and SHA-256-verified artifacts. (Stand-alone underfill 7/7 and framework truncated 7/7 content checks were confirmed on re-verification after a verifier staging bug was fixed.)

## What round 3 says about "does the framework make the agent think?"

- **The hypothesis did NOT hold in the favorable direction.** On deliberately incomplete/ambiguous inputs, the framework's overhead *increased* with task complexity (27k–28k tok vs lean-round's 17k) while the lean standalone arm's completions stayed trivially cheap and scored as well or better under the same objective checks.
- **Quality of comprehension, read manually:** both arms' prose deliverables are genuinely strong on the comprehension dimensions — the standalone underfill doc found 7 gaps with safe/reversible defaults for each; both truncated-message docs cleanly separated facts from inference, assigned confidences, refused to assert a cause, and drafted replies that did not promise deadlines. There is no visible comprehension gap attributable to lacking a framework in these single-pass tasks.
- **Where the framework machinery did real work:** on the dashboard task it produced desktop+mobile screenshot evidence and its own offline-failure test harness (the FEED_URL "violations" are that harness in action), plus tamper-evident `audit_valid` records the standalone arm structurally cannot produce.
- **Two framework-side findings:** (1) the deadline/budget/step guard trio fired *at the delivering phase* on 2/3 complex tasks after work was done — the preflight fix from round 2 handles input estimation, but output-heavy deliverables still race the guards; (2) the verification policy mis-fired on a brief that forbids citations ("does not cite a source URL" flagged as error) — a policy/brief alignment defect worth fixing in `aeon_worker` verification.
- **One genuine infrastructure caveat:** the truncated message's first framework run was killed mid-execute (15,069 tok) by a local-stack outage, not by the model or the framework; it was retried on a fresh key with the same brief.

## caveats (round 3)

- Still exploratory: 3 tasks × 1 seed per arm, single model, no ordering control.
- Manual adjudication decisions are recorded explicitly in `verification-round3.json` and `usage-round3.json` so they can be re-checked.
- Framework token totals include the killed first attempt of the truncated task only in the separate job record, not in its retry's counts.
