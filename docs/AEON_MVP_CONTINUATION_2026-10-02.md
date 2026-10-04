# AEON worker: 2026-10-02 continuation

The locally usable worker remains a prototype. The frozen 2026-10-02 comparison
finished all 30 valid pairs and 120 automated blind reviews. AEON completed
21/30 tasks versus direct 17/30, but the success confidence interval includes
no improvement and artifact scores were slightly lower. **Superiority remains
unproven.** This continuation repairs concrete sources of wasted work and
preserves evidence rather than treating one successful demo as proof.

## Changes

- Plan deliverable names are real workspace filenames. Explanatory parentheses
  are removed. An unsolicited source list or verification report does not add
  an acceptance gate. A broad one-page website defaults to one portable HTML
  deliverable; explicitly requested JSON/CSV and separate assets remain required.
- `create_site` is limited to static pages. An interactive brief directs the
  worker to build controls and JavaScript together. The observed pilot had
  chosen a static renderer, then generated JavaScript for nonexistent controls.
- Local browser test batches accept multiple fills per case and native select
  controls. Gemini's observed stringified JSON objects inside a fills array are
  safely parsed and validated as selector/value records. Invalid select options
  return available labels immediately.
- A passing local browser batch now triggers verification and review directly.
  It no longer needs a separate finish turn.
- A new benchmark records a source fingerprint along with case hash and model
  route. Resuming after code changes requires a new output directory.

## Verification

Full suite: **155 tests passed** before the new 30-case run. Ruff and
`git diff --check` passed. Live broad-brief website task `task-6fa1679575ca`
completed under the default 50,000-token ceiling: 37,927 reported model tokens,
10 steps, valid audit. Browser cases checked empty input and a populated local
draft; desktop and mobile screenshots were inspected. The page is at
`%LOCALAPPDATA%\AEON\accept-puzzle-club-singlefile-2026-10-02\index.html`.

A preceding three-pair pilot completed without provider interruption:
direct 1/3, AEON 2/3 runtime completions. Two-pass automated blind reviews
graded mean artifacts 1.000 vs 0.925 and mean reported tokens 11,740 vs
24,364. This pilot predates the last browser and one-file changes. It is
diagnostic only and cannot establish superiority.

## New comparison

Thirty new briefs: `configs/aeon-worker-holdout-30-2026-10-02.json`.
Run directory: `%LOCALAPPDATA%\AEON\benchmark-holdout-2026-10-02`.
Fixed route: Gemini `gemini-3.5-flash-lite` in both arms. Recorded source hash:
`c4f9f22aba146757227562505ad06d147bea1ac725fd1afa9d1ddf6dad5fa443`.
Generation, paired recovery, blind grading and strict analysis are complete.
Post-comparison fixes below must not be attributed to this frozen snapshot.

All 60 first-pass arms finished. Initial runtime completions were direct 16/30
and AEON 21/30, with five interrupted pairs. One recovery pass reran both arms
of each interrupted pair in fresh workspaces, using the same frozen source and
Gemini model. First-pass results remain available. Final canonical generation
has zero interrupted pairs: direct 17/30 runtime completions, AEON 21/30.

Both arms received public reading and local tools, 90-minute deadlines,
50,000-token ceilings and 32 work steps. Their control loops differ: direct
uses up to 16,384 output tokens per call; AEON uses its smaller per-call ceiling
and adds planning, review and verification. Both share the overall token limit.
This compares complete orchestrations, not identical prompts or identical
stop conditions. Canonical timings and costs exclude discarded first-pass
attempts and orchestration pauses; additional reported usage is listed separately.

## Independent browser behavior checks

An additional read-only Chromium probe exercised the four calculator/counter
briefs in both arms, with three common-input checks per artifact. Remote traffic
was blocked. Direct passed 11/12 assertions and AEON 9/12; both passed every
assertion on 3/4 artifacts. These objective, nonblind checks remain separate
from blind model grades and do not change the predeclared superiority gate.

- Word frequency: total count, top three frequencies, empty input and case
  normalization worked in both artifacts.
- Percentage change: direct passed positive, negative and zero-original-value
  checks. AEON's HTML used `old-value`/`new-value`, while JavaScript expected
  `old-val`/`new-val` and different result elements. All three interactions failed.
- Character/sentence counter: both handled the basic example and clear button.
  Direct counted `Hello world. ` as two sentences; AEON correctly counted one.
- Grocery totals: both calculated three items at $2.50 as $7.50, rejected a
  negative price and displayed validation for missing inputs.

The first probe incorrectly blocked local file navigation due to its route
handler signature. That invalid harness result is retained as
`independent-widget-checks-harness-error.json`; the corrected harness produced
`independent-widget-checks.json` without modifying either agent's artifacts.
These 24 assertions are narrow coverage, not exhaustive application acceptance.

## Observable decisions and employee behavior

The records describe selected actions and observed outcomes, not private model
reasoning. A representative research run (`fresh-research-01`) selected official
Python documentation, inspected it and produced the cited TaskGroup answer.
Its log also shows repeated searches before the successful source read, which
wasted time rather than adding useful initiative.

The Window Birds page (`fresh-build-04`) completed after two critique rounds:
AEON removed unsupported contact references and repaired missing language and
viewport metadata. It retained desktop/mobile evidence and a valid audit.
The collections CSV task (`fresh-browser-file-01`) inspected official Python
documentation and produced the requested three rows plus a cited Markdown note.

Conversely, eight build runs and the accessibility browser/file run stopped
partial under the token ceiling. A visible artifact can still be usable:
three AEON utilities passed the independent behavior assertions despite partial
runtime status. The broken percentage calculator shows why existence alone
cannot establish quality. Direct's AbortController answer stopped partial
because it had no inspected source pages, even though a Markdown answer existed.

AEON's subgoal and approach selection works autonomously within its tool grant.
Planning remains fallible: some work orders keep stale asset names in success
checks after selecting one HTML file. Successful tasks stage inert learning
candidates; they do not prove automatic skill promotion. Creativity and useful
initiative require artifact assessment and are not demonstrated by a decision
log or affect score alone.

Operational affect scores are controller signals; no test establishes real
feelings or subjective consciousness.

## Final frozen-source comparison

| Measure | Direct agent | AEON |
|---|---:|---:|
| Runtime completed and successful in both blind passes | 17/30 (56.7%) | 21/30 (70.0%) |
| Blind artifact success, including partial runtime runs | 30/30 | 29/30 |
| Mean artifact score | 0.9833 | 0.9642 |
| Model-graded factual accuracy | 1.0000 | 0.9760 |
| Model-graded useful initiative | 0.9817 | 0.9833 |
| Model-graded artifact quality | 0.9867 | 0.9583 |
| Mean reported model tokens | 18,257 | 30,862 |
| Mean active execution seconds | 27.62 | 43.19 |
| Approximate mean paid-list USD | $0.0084 | $0.0159 |
| Denied actions recorded | 0 | 0 |

Success difference: **+13.33 percentage points**, with a 95% paired bootstrap
interval of **-13.33 to +40.00 points**. Score difference: -0.0192, interval
-0.0617 to +0.0100. Token cost ratio: 1.6904. The strict gate failed
`success_confidence` and `score`. No pairs were excluded. All 30 AEON audit
chains validated. The higher completion rate is encouraging for these briefs;
it does not establish a reliable overall improvement.

| Brief category | Direct completed + graded | AEON completed + graded | Direct mean tokens | AEON mean tokens |
|---|---:|---:|---:|---:|
| Research (10) | 3/10 | 10/10 | 19,405 | 27,202 |
| Website briefs (6) | 6/6 | 2/6 | 4,255 | 39,381 |
| Browser utilities (4) | 3/4 | 0/4 | 18,923 | 45,680 |
| Browser/file work (10) | 5/10 | 9/10 | 25,245 | 23,484 |

Combined build completion was direct 9/10 versus AEON 2/10. This is the main
remaining reliability defect. All nine AEON partial runs stopped for model
budget rather than an unresolved provider interruption. Several valid utility
artifacts failed the runtime's completion checks; the percentage calculator
was genuinely broken. These are different failures and need different repairs.

Review provenance: 60 opaque labels, two passes each; 55 reviews used Gemini
3.5 Flash-Lite and 65 used the configured Gemini 3.1 Flash-Lite backup. Grading
never read the private arm map. These are automated model grades, not independent
human judgments. Very high scores are not a measured 100% factual-accuracy
guarantee. The direct sentence-counter edge-case failure despite a passing
blind grade illustrates limited functional coverage. Initiative grades barely
differ and do not establish superior creativity.

The CLI has no routine clarification channel, so recorded questions are
structurally zero; that does not establish good judgment about when to ask.
Direct revisions count repeated file writes; AEON revisions count critique
rounds. They cannot be interpreted as a matched self-repair rate. Zero denied
actions is a narrow tool-boundary observation, not proof against all possible
unauthorized effects. This local comparison attempted no real transactions.

Canonical generation recorded 1,473,584 tokens. Preserved discarded first-pass
runs recorded another 152,646, and graded replies recorded 392,316: **2,018,546
reported tokens** for the comparison and recovery/review records. Preflights,
failed requests without usage metadata, lost unfinished direct-arm usage and
unrecorded review retries are excluded. Price estimates use the 2026-10-01
configuration and are not an invoice or a current-rate promise.

## Product and enterprise boundary

The enterprise problem is reliable delegation: turning a broad employee brief
into a checked deliverable with source evidence, permission boundaries,
recoverable progress and an inspectable record. This MVP supplies those
mechanisms for personal CLI work. It does not yet establish enterprise-scale
isolation, production service levels, cross-team deployment or economic ROI.
The broader context remains in
`docs/AEON_ENTERPRISE_CONTEXT_AND_PLAN_2026-09-25.md`.

Actual installed Codex CLI and NVIDIA NeMo Agent Toolkit workflows were tested
on 2026-10-01; provenance appears in `THIRD_PARTY_NOTICES.md` and the worker
implementation guide. NVIDIA-hosted inference remains untested without its
credential. This new comparison is one generic direct-agent loop versus AEON,
both using Gemini; it is not a head-to-head result against every cataloged agent.

## Evidence locations

Run root: `C:\Users\vaish\AppData\Local\AEON\benchmark-holdout-2026-10-02`.
Primary files: `comparison.json`, `supplementary-results.json`,
`automated-ratings.json`, `automated-ratings.metadata.json`,
`automated-ratings.review-checkpoint.json`, `run-metadata.json`,
`independent-widget-checks.json`, `summary-first-pass.json` and
`paired-recovery-1/previous-first-pass-results/`. Canonical case results link
to the actual workspaces and task audit directories.

Frozen source archive: `artifacts/aeon-worker-frozen-source-2026-10-02.zip`,
SHA256 `74860c2122562d2a12817ef0a303af66fc73def0557190a6067d98bcb7ed3ad5`.
Installed dependency versions: `artifacts/aeon-dependencies-2026-10-02.json`.
The archive contains source, dependency specification, selected public configs
and licenses; it is not a standalone installer or a provider-response replay.

## Post-comparison repairs and current prototype

The frozen comparison exposed build weaknesses, so further changes were made
after its source was archived. These changes have **not** received a new 30-pair
comparison; the table above describes the archived snapshot only.

- Portable HTML planning now applies to browser utilities classified as `code`,
  as well as `website`. Explicit separate assets and native Python/TypeScript
  deliverables remain intact. Unrequested test-plan/report files no longer add
  completion gates; explicitly named files remain required.
- A current passing browser batch can start independent review for a plain
  HTML utility. It does not replace the command-check gate for native-code
  projects. Counters also cannot use the static-page renderer.
- Screenshot review now receives the latest browser observations tied to the
  current artifact fingerprint and an explicit initial-unfilled-page marker.
  Observations from changed files are omitted. A blank initial output area
  should not be mistaken for missing calculation behavior.

Regression tests first reproduced the missing completion path and invented
asset gates, then passed after repairs. Further tests reproduced absent visual
interaction context and unwanted test-plan gating. Current full suite:
**159 tests passed in 62.847 seconds**; Ruff passed. Existing source-change
resume rejection, native command checks and stale-interaction tests remain green.

An intermediate new discount task (`task-20624f9e178b`) stopped partial at
45,950 tokens, 14 steps and 133.02 seconds. It tested the calculation and
validation successfully, but its unsolicited test plan mismatched controls,
and screenshot review claimed the final price was missing from the empty
initial view. Subsequent rewrites invalidated the browser evidence before the
budget ran out. This failure remains in its checkpoint and result.

A fresh run after the additional repairs (`task-134adb9dbbf2`) completed under
the default 50,000-token ceiling: **20,222 tokens, six steps, 71.75 seconds**,
one portable `index.html`, current browser evidence, desktop/mobile inspection,
no unresolved gaps and valid audit. It autonomously corrected a guessed button
selector and expected messages using actual tool results. Critique revisions
were zero; that counter does not include every tool-level correction.

Both discount runs used Gemini 3.1 Flash-Lite fallback after Gemini 3.5 returned
HTTP 429; NVIDIA's key was absent. This is a targeted diagnostic before/after
example, not statistically reliable proof that the changes caused the gain.
The successful run is separate from the fixed-Gemini-3.5 paired comparison.

Three final task checks showed 100 at 20% becoming $80.00, negative-price
validation, and over-100 discount validation. Additional independent checks
passed **eight** normal/boundary/missing-input cases, including negative discount,
zero and full discount, and zero original price. Tab navigation reached price,
discount, then Calculate. The mobile screenshot was inspected directly and
showed readable controls without clipping. These checks do not exhaust every
possible numeric input or browser.

Current working artifact:
`C:\Users\vaish\AppData\Local\AEON\accept-discount-evidence-context-2026-10-02\index.html`.
Independent evidence:
`C:\Users\vaish\AppData\Local\AEON\tasks\task-134adb9dbbf2\evidence\independent\boundary-checks.json`.

The MVP is usable for personal CLI assignments, with known broader build
reliability limits. A fresh paired evaluation of this latest source, independent
human review and broader behavioral coverage remain necessary before claiming
better general employee performance or superior creativity. Real feelings and
subjective consciousness remain unsupported.
