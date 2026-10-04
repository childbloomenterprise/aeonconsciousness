# AEON worker MVP acceptance record

2026-10-03 update: reusable worker 0.3 release adds an installable wheel, public
SDK/adapters, local preview caching and deployment guide. 169 tests passed;
clean Windows wheel installation plus Chromium desktop/mobile checks passed.
See `AEON_RELEASE_0_3_0_2026-10-03.md`. Records below retain their dated scope;
the 30-pair superiority gate still failed and has not been rerun for this source.

Updated 2026-10-02. Current continuation evidence is in
`docs/AEON_MVP_CONTINUATION_2026-10-02.md`; older dated sections below preserve
historical attempts. A completed CLI task means its mechanical checks and
independent review passed under its stated budget. It does not establish that
AEON outperforms a direct agent or has subjective experience.

| Requirement | Current evidence | Status |
|---|---|---|
| CLI start/status/resume/result, separate checkpoint and audit | `aeon_worker`; task results with valid hash-chain audits | Pass |
| Typed work order, subgoals, sources, actions, findings, artifacts | `aeon_worker/models.py`; worker tests | Pass |
| NVIDIA primary, Gemini fallback, route recording | Router tests and live Gemini results | Pass for fallback; NVIDIA live route unavailable without key |
| Public research, browser, workspace editing, bounded checks | Live acceptance tasks and tool tests | Pass for first-release formats |
| Task-grant boundary | Denial/domain/spend tests; blocked-action gap test | Pass for tested tool paths; no real transaction attempted |
| Research written answer with citations | Live `task-e041ac2b0cf3`, completed, inspected official Python docs, 9 steps, 29,602 tokens, audit valid | Pass |
| Broad-brief responsive website | Latest live `task-6fa1679575ca`, completed under default 50,000-token ceiling: 37,927 tokens, 10 steps, local draft checks, desktop/mobile screenshots, image review, valid audit | Pass for this demo; wider reliability remains open |
| Website form truthfulness and behavior | Chromium submit test showed local confirmation and zero HTTP requests; visible no-backend notice | Pass for this demo |
| Browser-plus-file assignment | Live `task-cbde35a5faca`, completed from default 50,000-token ceiling in 6 steps, inspected Python docs using browser and focused page reads, checked 3-row CSV, audit valid | Pass |
| Fault recovery | Tests for invalid citations, failed compile then repair, broken layout then repair, interrupted/resumed task, provider failure, and token/step ceilings | Pass for simulated faults |
| Arun Guinness case | Live `task-af25e8d86d88`, completed after resume: `index.html` plus `source_note.txt`, inspected YouTube name-only evidence explicitly limited, unsupported official/profession/location claims repaired or labeled, desktop/mobile visual review, valid audit, 53 steps and 145,966 recorded tokens under legacy retry accounting | Pass, but inefficient and not independently fact-confirmed |
| Existing AEON regression | Current full suite: 159 tests passed after post-comparison fixes; frozen comparison source previously passed 155; Ruff passes | Pass |
| Local interactive verification | Real Chromium calculator test and full scripted worker loop; observed result retained; later file changes invalidate the check | Pass: live task-accda8040d26 completed after explicit budget extension; 3 observed browser assertions, desktop/mobile image review, 49,515 tokens, valid audit |
| Thirty paired briefs | Frozen 2026-10-02 run: 30 valid pairs after five paired recoveries, 120 automated blind reviews, zero interrupted pairs remaining | Complete; subsequent fixes have separate diagnostic evidence |
| Employee-standard superiority gate | Completed + blind success: direct 17/30, AEON 21/30; +13.33 points, 95% interval -13.33 to +40; lower AEON mean artifact score | **Unproven**; confidence and score gates failed |
| Default-budget browser utility after comparison | task-134adb9dbbf2 completed: 20,222 tokens, 6 steps, valid audit, 3 current browser cases; 8 additional input checks and Tab navigation passed | Pass for this demo; current-source superiority untested |
| Subjective consciousness or feelings | Operational confidence/curiosity/concern recorded, no subjective-experience test | Not claimed |

The diagnostic benchmark exposed real worker defects as well as Gemini HTTP
429 interruptions. Subsequent changes fix fragmented documentation lookups,
false HTML-handler errors, excessive research loops, premature token exhaustion
after files exist, and missing blocked-action reporting. Because these changes
followed inspection of the diagnostic set, that set is no longer held out for
a superiority claim. A new held-out, provider-stable 30-pair run and blind
artifact ratings remain required. The original diagnostic files remain intact
for inspection.

Fresh balanced cases are in `configs/aeon-worker-benchmark-holdout-30-v2.json`.
The benchmark runner now retries both arms of a provider-interrupted pair in
fresh directories, preserving previous results, and can pause between arms to
respect provider rate limits. A fresh run started on 2026-09-30 under
`%LOCALAPPDATA%\AEON\benchmark-holdout-2026-09-30`; first-pass run finished all 60 arms: direct 9/30 completed, AEON 9/30 completed, with 14 provider-interrupted pairs. Both-arm retries and two-pass automated blind grading finished; final diagnostic results appear below. Five pairs were cached when the original process stopped.
The resumed process preserves Gemini `gemini-3.1-flash-lite` in
`run-metadata.json`; changed case sets or mixed cached routes are rejected.
Further general correctness changes landed after this process loaded its code:
independent-review failure now prevents completion on every path, and reported
tokens from malformed model responses/retries now count in both arms; browser
previews additionally block ungranted non-read HTTP requests; site creation
preserves promised secondary deliverables. This run
therefore evaluates the earlier loaded snapshot and cannot establish superiority
for the latest code. HTTP failures without provider usage data remain unmetered;
reported token totals and list-price estimates are not an actual invoice.
Browser previews now reject non-read HTTP methods until an explicitly granted
browser action activates the domain guard. Automated blind review is available
through `aeon benchmark review`; a live two-artifact smoke run passed. It never
reads the private arm map, records model-review provenance, and checkpoints
grades against artifact fingerprints. Its grades remain weaker evidence than
independent human review, especially for interactions inspected only statically.
The latest browser tool also supports `navigate_local` followed by workspace
click/fill actions without an external grant. Interactive HTML completion now
requires a successful click observation tied to the current HTML/CSS/JS artifact
fingerprint. This proves an interaction was observed, not that every possible
input or acceptance condition passed; independent review also receives the
observations and command-check results.

The MVP is usable for the three general CLI tasks and the Arun case. Wider
reliability and the employee-standard comparison remain open. Arun's public
identity and career were **not** independently confirmed; the site labels
owner-provided claims and the source note states that limit.


## Additional release evidence, 2026-10-01

- Real NVIDIA NeMo Agent Toolkit 1.9.0 workflow registered, validated, and run
  through `nat run`: task-9d2cd175321f completed, 33.16 seconds, 8,264 tokens,
  checked three-item JSON, audit valid. The model was Gemini fallback, not a
  live NVIDIA-hosted model; NVIDIA_API_KEY is absent.
- Installed Codex harness reused for structured inference. Smoke request passed.
  Worker task-275b8783ec61 completed after recovery and explicit ceiling
  extensions from 100,000 to 180,000 tokens; 179,398 reported tokens, 349.2
  seconds, valid audit. High inference overhead prevents an efficiency claim.
  Configured default model identity is not verified; this route is not paired
  against the fixed Gemini benchmark.
- Task-54a07281af13 corrected inaccurate calculator documentation after five
  actual browser tests; completed in 25,004 tokens under default 50,000 ceiling.
- Failed attempts remain in checkpoints: source-free tasks misclassified as
  research, absolute promised paths, missing selectors, unsupported PASSED
  claims, repeated oversized context and budget exhaustion. Fixes target those
  concrete defects; they do not retroactively improve benchmark results.
- Fresh interactive task-accda8040d26 completed after a 30,000-token ceiling
  extension. Total reported usage was 49,515, but it did not finish in one
  default-ceiling pass because conservative reservation prevented final review.
  Three current browser assertions passed; image review inspected both layouts.

Framework integration usage and provenance: `docs/AEON_WORKER_MVP_IMPLEMENTATION.md`
and `THIRD_PARTY_NOTICES.md`. Final diagnostic benchmark results follow below. Supremacy and subjective consciousness remain unproven.

- Fresh Codex release run task-dd0ef3ea97fa completed in one pass under an
  explicitly selected 100,000-token integration-test ceiling: 74,107 tokens,
  91.64 seconds, no revisions, checked JSON, valid audit. This supersedes the
  earlier recovery run as current integration evidence, but still exceeds the
  default 50,000-token allowance. Apps, plugins and child-agent tools are disabled
  in the inference subprocess in addition to shell tools and web search.

- Native Gemini tool-action schema smoke passed. Structured-content failures
  now produce `invalid_model_response`, not `provider_unavailable`. Live
  task-149b746f8b43 completed in 11.16 seconds, 6,499 tokens, valid audit under
  default ceiling. Benchmark generation predates this change.


## Final diagnostic comparison, 2026-10-01

Recovery: direct 10/30 runtime completions, AEON 12/30; seven interrupted
pairs remain. Two blind passes produced 120 ratings. Completed-and-graded
success: direct 8/30 (26.7%), AEON 12/30 (40%). Blind artifact success,
including useful partial runs: direct 27/30, AEON 20/30. Mean artifact
scores: 0.9408 vs 0.7142; mean tokens: 8,956 vs 26,159. AEON did not show
better overall artifact quality or efficiency.

Only 23 pairs qualify for paired diagnostic calculations. Success gain
+21.74 percentage points has a 95% paired bootstrap interval of -13.04
to +56.52 points. Superiority is unproven; sample size, success-confidence,
score and cost gates fail. Reviews are automated, generation used older
loaded snapshots, and this set cannot certify the final implementation.

Latest default-budget website task-6c32e94943d1 passed three browser cases
but stopped partial at 46,585 tokens; explicit ceiling/deadline extensions
initially returned partial after review. A regression-tested fix for negated
research then allowed checkpoint completion: 68,381 tokens, 24 steps, five
revision rounds, three current browser assertions, desktop/mobile inspections
and valid audit. This still required extensions; Default-budget website reliability remains open.

Full results, provenance, limitations and usage:
`docs/AEON_MVP_RELEASE_2026-10-01.md`.
