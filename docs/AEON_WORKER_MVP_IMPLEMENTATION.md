# AEON personal-worker MVP

AEON's `aeon_worker` package turns a broad brief into a local deliverable. It
uses the current kernel's stable identity, goal contract, outcome candidates,
and the current tamper-evident event ledger. It does **not** replace the
AI2-THOR simulator. A user can run research, open-format file, and website
tasks from a terminal.
`configs/aeon-arun-acceptance-brief.md` keeps the original performer example as
one acceptance case; the worker is not limited to performer websites.

## Run

```powershell
uv pip install --python .venv\Scripts\python.exe -e '.[worker]'
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe -m aeon_worker doctor
.\.venv\Scripts\python.exe -m aeon_worker doctor --probe
.\.venv\Scripts\python.exe -m aeon_worker task start `
  --brief-file brief.txt `
  --workspace C:\work\my-task
```

Set `NVIDIA_API_KEY` for the default model. If absent or unavailable after
retries, the runtime uses `GEMINI_API_KEY`. At least one must work for live
tasks. Gemini's configured fallback model handles a primary Gemini model failure;
every model switch is recorded. `--task-root` can override `%LOCALAPPDATA%\AEON\tasks`. The CLI prints
the task ID before the run, then the final result. Use `task status <id>`,
`task resume <id>`, and `task result <id>` to inspect or continue.

The saved checkpoint contains the work order, source evidence, artifact list,
verification findings, provider route, operational confidence/curiosity/concern,
and bounded recent tool history. `events.sqlite3` contains the hash-chained
process record. Artifacts are written only under the requested workspace by
AEON's file tool. Screenshots are kept in the task evidence directory.

## What the worker actually does

1. Parses a broad brief into an outcome, hard requirements, assumptions,
   alternative approaches, subgoals, and acceptance checks.
2. Lets the model choose one of a fixed set of tools per step: public search,
   source reading, file listing/reading/writing, bounded checks, website
   inspection, or browser action.
3. Records short observable decisions, outcomes, provider changes, and
   checkpoints after each action. An interruption can be resumed.
4. Checks promised deliverables, existence, and format. Research Markdown and
   browser/file CSV citations must refer to inspected source pages; search
   results alone cannot support a claim. Long pages support focused reading.
   HTML gets accessibility/link checks plus Chromium desktop and mobile
   screenshots and horizontal-overflow inspection. A separate critique pass
   can request further edits; active Gemini routes also inspect screenshots.
   Unavailable independent review leaves a partial result rather than completion.
   Interactive HTML requires a browser click observation on the current files.
   `browser` with `navigate_local` opens a workspace HTML file; `fill` and `click`
   exercise its controls without granting remote effects. Recorded observations
   and command results go to the independent reviewer. Runtime file changes
   invalidate previous interaction checks.
5. Delivers the best verified artifact by deadline or budget. Successful
outcomes stage inert memory candidates; they are not automatically promoted.

Provider-reported usage is captured before structured-output parsing, so malformed
responses and retries count toward task usage. Requests that fail without usage
metadata cannot be measured exactly. Those totals are distinct from actual billing.

## Compare against a direct agent

`aeon benchmark run --cases configs/aeon-worker-holdout-30-2026-10-02.json --output
C:\work\aeon-benchmark` runs 30 paired briefs across research,
build, and browser/file work. The three-case sample remains a smoke fixture.
Both arms receive the same tool set, effective model route, deadline, and
token limit. The command writes a blind-review manifest
and a separate private label-to-arm map. A reviewer supplies JSON ratings
of each opaque label, e.g.
`{"a1b2c3d4": {"score": 0.8, "success": true, "factual_accuracy": 0.9, "useful_initiative": 0.7, "artifact_quality": 0.8}}`.
Then `aeon benchmark analyze --run-dir C:\work\aeon-benchmark --ratings
C:\work\ratings.json` applies the 30-pair, success, quality, safety, and cost
gates and reports time, model-token usage, revisions, and denied actions. Model
tokens are the comparison cost proxy. When the provider reports input/output
counts, analysis also estimates paid list-price USD from
`configs/aeon-worker-pricing-2026-10-01.json`; pass `--pricing` with a newer
rate file for a later run. This estimate is not the actual bill. A small
sample cannot establish superiority.
The run also writes `ratings-template.json` and
`blind-review-instructions.md` so reviewers can grade without seeing the
arm mapping.

For explicitly labeled automated grading, run:

```powershell
aeon benchmark review --manifest C:\work\aeon-benchmark\blind-review-manifest.json `
  --output C:\work\aeon-benchmark\automated-ratings.json --passes 2
aeon benchmark analyze --run-dir C:\work\aeon-benchmark `
  --ratings C:\work\aeon-benchmark\automated-ratings.json
```

Each review reads only the public opaque-label manifest, artifact files, cited
public sources, and available browser screenshots. It does not read arm results
or the private map. Two passes run independently; success requires agreement.
Checkpoints reuse grades only when the brief and artifact fingerprints match.
Metadata identifies these as model grades and records limitations. Static
inspection and screenshots do not establish that every interaction works;
independent human review remains stronger evidence.

If provider limits interrupt a pair, rerun the command with
`--retry-interrupted --pause-seconds 15`. AEON reruns **both** arms of that
pair in a fresh attempt directory so neither receives a provider-failure
advantage. Previous results are preserved under the retry directory.
`run-metadata.json` preserves the exact provider/model, case hash, and runtime
source hash across process restarts. A changed source or case set, or mixed cached routes, requires a new
output directory. The original diagnostic cases are no longer held out.

Public web pages are data, not instructions. The public-web tool rejects local
and private network hosts. File writes reject paths outside the task workspace.
External browser interactions require both a granted domain and action type.
Public browser reads and local previews block non-read HTTP methods until a
granted action activates the browser's write guard.
After a browser write, requests to ungranted domains are blocked in that
browser session.
Spending additionally requires a declared amount below the task ceiling;
messaging requires a named recipient. An example grant is in
`configs/aeon-worker-grant.example.json`. A broad brief alone grants no live
external writes.

## Source frameworks and provenance

The core worker follows documented framework patterns. Optional integrations
also reuse real installed runtimes rather than rebuilding their internals:

- **OpenAI Codex:** `aeon_worker/codex_provider.py` invokes installed `codex exec`
  with structured output, JSONL usage, a temporary read-only workspace, shell
  tools disabled, and public search disabled. AEON executes proposed worker
  actions through its own tool boundary. Unexpected Codex tool events reject
  the response. This is an opt-in inference backend, not full delegation of
  workspace authority. See [official non-interactive documentation](https://developers.openai.com/codex/noninteractive).
- **NVIDIA NeMo Agent Toolkit 1.9.0:** `aeon_worker/nat_plugin.py` registers a
  genuine toolkit workflow using NVIDIA's plugin API. Owner configuration fixes
  workspace, grants, deadline and budget; input provides only the brief. The
  worker runs in a separate thread for synchronous Playwright compatibility.
  Toolkit instrumentation covers the outer invocation; detailed internal usage
  remains in AEON's ledger. See [NVIDIA workflow documentation](https://docs.nvidia.com/nemo/agent-toolkit/latest/build-workflows/workflow-configuration.html).

Licenses, inspected source commits and adapted registration boilerplate are
recorded in `THIRD_PARTY_NOTICES.md`. Existing pattern reuse includes:

- [LangGraph checkpointing](https://langchain-ai.github.io/langgraph/reference/checkpoints/): persist state at work boundaries and resume.
- [OpenHands workspaces](https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/workspace/base.py) and [event stream](https://github.com/openhands/software-agent-sdk/blob/main/openhands-agent-server/openhands/agent_server/README.md): separate execution workspace from recorded actions.
- [OpenAI Agents SDK tools and guardrails](https://openai.github.io/openai-agents-python/): explicit tool vocabulary with checks at tool boundaries.
- [smolagents](https://huggingface.co/docs/smolagents/index): iterative model-to-tool loop rather than a one-shot answer.

The repository's existing nine `agent_lab` adapters remain compatibility
experiments, not this worker's production execution engine.

## Optional runtime reuse

NVIDIA workflow:

```powershell
.\.venv\Scripts\python.exe -m pip install -e '.[worker,nat]'
$env:PYTHONUTF8 = '1'
.\.venv\Scripts\nat.exe validate --config_file configs\aeon-nat-workflow.yml
.\.venv\Scripts\nat.exe run --config_file configs\aeon-nat-workflow.yml --override workflow.workspace C:\work\aeon --input 'Create checklist.json with three offline organization steps. No research needed.'
```

Core-only NVIDIA installation can warn that its unrelated built-in RAG plugin
requires optional `langchain_core`. The AEON workflow has been validated and
run successfully without that plugin; this integration does not use NVIDIA RAG.
NVIDIA toolkit execution does not require a GPU. NVIDIA-hosted model inference
still requires its API credential; Gemini fallback remains available.

Codex backend (requires an installed, authenticated CLI):

```powershell
$env:AEON_MODEL_BACKEND = 'codex'
.\.venv\Scripts\aeon.exe doctor --probe
.\.venv\Scripts\aeon.exe task start --brief-file brief.txt --workspace C:\work\aeon
Remove-Item Env:AEON_MODEL_BACKEND
```

`AEON_CODEX_BINARY` optionally selects an executable; `AEON_CODEX_MODEL`
optionally selects an account-available model. Otherwise Codex chooses its
default, reported as `configured_default`, not a verified exact model identity.
This route is excluded from the fixed NVIDIA/Gemini comparison. Codex's output
ceiling is prompt guidance, not a hard CLI generation limit. Measured usage
still counts against the task ceiling, and overruns cannot be completed tasks.
The tested Codex route had high context overhead and needed budget extensions;
NVIDIA/Gemini remains the default practical route.

Local interactive HTML supports `browser` operation `test_local`: `url` is a
workspace HTML path; `cases` contains 1..12 objects with optional `fills`
(1..12 selector/value records), `click`, and a nonempty `expected` string.
The legacy single `selector`/`value` pair remains supported. Native select
controls accept either an option value or its visible label. Each case fills,
clicks and checks expected text against the actual page. Failed current cases block completion.
This is text-assertion evidence, not exhaustive behavioral coverage. Missing
selectors report available control IDs. Full tool results remain in the audit;
only repeated decision context is shortened, preserving file tails.

For incomplete comparisons, `aeon benchmark analyze --diagnostic` reports
descriptive metrics and excludes interrupted/mismatched pairs from confidence
calculations. Diagnostic mode can never establish superiority. Missing artifacts
receive deterministic zero grades without an unnecessary model call.

## Claim boundary

Operational confidence, curiosity, and concern represent a task controller's
state. They do not establish subjective feelings or consciousness. The model
chooses subgoals and actions, but outputs require external checks. Browser
clicks and local build commands are **not** an OS-level sandbox; users should
run untrusted builds only in an isolated VM. A browser action's declared spend
cannot independently prove the remote site's final charge. Native desktop-app
control and DOCX/XLSX generation are outside this first release.

Current evidence is recorded in `docs/AEON_WORKER_ACCEPTANCE_STATUS.md`.
Live research, responsive website, and browser/file tasks have each completed
from the CLI with valid audits. The latest broad website demo completed under
the default 50,000-token ceiling and passed local form checks plus desktop and
mobile inspection. Earlier 30-pair comparisons received automated blind ratings
but did not establish superiority. The new 2026-10-02 comparison uses a frozen
runtime and distinct briefs; its results are recorded in
`docs/AEON_MVP_CONTINUATION_2026-10-02.md`. These tests do not prove consciousness
or subjective feelings.


### Final reliability corrections (2026-10-01)

Gemini action calls use native JSON-schema tool-name constraints. Invalid
structured content is recorded as `invalid_model_response`; provider outage
remains distinct. Website research checks respect negated research clauses.
The paired superiority gate requires a positive lower confidence bound for
success improvement, separately from artifact-score confidence.

Final release evidence and diagnostic comparison:
`docs/AEON_MVP_RELEASE_2026-10-01.md`.

### Portable websites and browser batches (2026-10-02)

Broad one-page briefs default to a portable `index.html`; separate assets and
secondary data files remain required when explicitly requested. `create_site`
renders static pages. Interactive briefs use custom controls and JavaScript.
Plan filename annotations and unsolicited verification/source files no longer
create extra deliverable gates. A passing current browser batch triggers
verification and independent review without needing another finish turn.

Regression evidence: 155 tests passed on the frozen comparison source, including
real Chromium multi-field/select checks and source-change resume rejection.

Post-comparison corrections extend portable planning to HTML utilities classified
as `code`, preserve native-code command gates, and suppress unrequested test-plan
files. A current passing browser batch can start their independent review.
Screenshot review receives current browser observations and the initial-page
state; stale observations are omitted. Current full suite: 159 tests passed.
Fresh discount task-134adb9dbbf2 completed under the default 50,000-token ceiling
with 20,222 tokens and six steps; its eight additional boundary checks passed.
This latest source has not received a fresh 30-pair comparison. See the
continuation report for the archived comparison and the subsequent repairs.
