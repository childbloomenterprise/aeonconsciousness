# Layout repair and efficiency investigation — 2026-10-09

## Conclusion

Original intermittent layout assertion cause **unresolved**. No speculative
runtime fix. Original `revisions >= 1` assertion preserved. New assertions
require explicit initial desktop/mobile overflow and clean final inspections.

One fault-injected mechanism reproduces the original signature: a transient
failure in the first explicit `inspect_site` call leaves no mechanical
verification revision. The scripted provider then writes the repaired HTML;
fresh verification passes, yielding `completed` and `revisions = 0`.
The original assertion fails. This does **not** establish what happened in the
Oct 8 run: its original tool result and command output were not saved.

`revisions` counts verification-triggered revision cycles, not every artifact
rewrite or every recovery from a failed tool call. Production does verify the
corrected artifact in the injected case. Inflating this counter would obscure
its present semantics and would not repair an identified artifact defect.

## Tests and evidence

| Check | Result | Evidence |
| --- | --- | --- |
| Original repair case under four concurrent Chromium processes, each with a seeded random sibling browser case first | 64 repair cases + 64 sibling cases, 128/128 passed, 73.719 s | `order-contention/summary.json` |
| Every observed browser inspection in stress | 263 inspections, zero exceptions; every repair result had at least one revision | `order-contention/lane-{0,1,2,3}/records.json` |
| Current strengthened repair case + local browser cases | 8/8 passed, 9.157 s | `focused-regression.log` |
| Same file URI rewritten bad → good → bad → good, reusing page/browser | Desktop/mobile overflow results correct; mobile DOM current marker, geometry and screenshot existence checked | `tests/test_local_browser_cases.py` |
| Injected first-inspection exception | Expected original assertion failure; clean final artifact completed, revisions 0, two inspection calls | `injected-failure-signature.json` |

Stress keeps source bytes/hashes, inspection results, post-call mobile geometry,
desktop/mobile screenshots, test outputs, result records and checkpoint tool
history. Its temporary workspaces disappear after tests; copied evidence stays.
Snapshots record the last mobile geometry because production inspection visits
desktop then mobile. Desktop screenshots and overflow result retained separately.

Artifacts occupy approximately 11.6 MB across 536 files. Keep detailed evidence
locally; release staging should select reports/harnesses deliberately.

Reproduce with dedicated interpreter and
`PLAYWRIGHT_BROWSERS_PATH=C:\Users\vaish\AppData\Local\AEON\enterprise-private\browsers`:

```powershell
& 'C:\Users\vaish\AppData\Local\AEON\enterprise-private\venv\Scripts\python.exe' artifacts/local-2026-10-09/layout/stress_layout.py --out artifacts/local-2026-10-09/layout/repeat-new --lanes 4 --repeats 16 --ordered
& 'C:\Users\vaish\AppData\Local\AEON\enterprise-private\venv\Scripts\python.exe' artifacts/local-2026-10-09/layout/probe_failure_signature.py
```

No model requests, genuine queue claims, or local server mutations performed.
Only assigned tests and this artifact directory changed.

## Demonstrated efficiency issues

`efficiency-evidence.json` reads only named existing task checkpoints and SQLite
event ledgers in read-only mode. It stores counts and classifications, excluding
credentials, prompts and provider response bodies. Snapshot predates current
recovery work: tip checkpoint remains interrupted; invoice finished Oct 8.

| Task | Recorded costs | Implication |
| --- | --- | --- |
| Invoice | 20,596 tokens; 18,310 input (88.9%); 9 calls; 7 decisions; final review 2,369 tokens (2,360 input/9 output) | Input repetition dominates. Final review exceeded available original 20,000-token allowance; explicit extension restored completion. |
| Tip calculator | 25,051 tokens; 18,670 input (74.5%); 8 decisions; 5 malformed `fills` failures | Failed browser-action decisions consumed 12,139 tokens, 48.5% of recorded task usage, before provider HTTP 400 interruption. |

Recommendations, in order:

1. Complete live provider/schema repair before optimization. Mock envelope success
   cannot show provider compatibility; malformed loop remains concrete evidence
   against the former schema/prompt combination.
2. After repeated identical validation errors, select a bounded alternative tactic
   (individual navigate/fill/click operations already available) instead of paying
   for the same failed compound operation. Retain errors, authority checks and
   current-artifact verification; never convert rejected actions into passes.
3. Reserve independent-review headroom while planning further actions. Remaining
   budget estimates must account for actual payload size and image costs; simply
   raising default limits does not establish efficiency.
4. Compare narrower decision context/schema and recent-result compaction against
   the existing behavior under matched provider, briefs and budgets. Input-heavy
   usage suggests a target, but these two tasks cannot prove savings or superiority.

No token optimization, memory promotion or behavioral runtime change made here.

## Follow-up: demonstrated browser-repair feedback defect — 2026-10-10

Read named tip checkpoint after provider recovery: status partial, 14 steps,
feedback empty. Three successive negative-case mismatches oscillated between
expected `Please enter a valid non-negative amount` and actual
`Please enter a valid non-negative bill amount.`. Targeted edits changed output
while the next test retained the prior wording. Saved `replace_text` history
contained only path, losing old/new excerpts. Normal and zero cases passed.

Parent implemented runner changes; this investigator owns tests only:

- `test_failed_negative_browser_case_guides_targeted_repair_and_current_retest`
  executes real normal/zero/negative browser cases in a temporary workspace,
  observes the failed input/error in the next decision's verification feedback,
  makes a targeted edit with preserved excerpts and verifies all cases against
  the current artifact. Its brief explicitly requires the expected wording so
  changing output is justified; wording not required by a real brief should
  instead lead to correcting the test expectation from observed behavior.
- `test_targeted_edit_history_keeps_excerpts_without_resending_whole_file`
  verifies bounded old/new excerpts reach the next decision and remain in
  checkpoint history, while approximately 4 KB of unrelated source content
  is excluded from decision context.

The parent runtime fix landed before the first test run. Accurate red evidence
therefore comes from a separate subprocess reverting only the two relevant
runner fragments **in memory**, preserving every runtime file and unrelated
working-tree change. Both regressions fail there: empty feedback and missing
old excerpt. Current fixed runner passes both plus existing targeted repair,
3/3 in 4.763 s.

Evidence: `probe_recovery_before_fix.py`,
`recovery-feedback-isolated-before.log`, `recovery-feedback-after.log`.
`recovery-feedback-first-after.log` preserves the original first run, which
already used the parent fix. No genuine task resumed or queue accessed here.
