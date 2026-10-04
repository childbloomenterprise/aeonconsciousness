# AEON employee autonomy blueprint

**Prepared:** 28 September 2026  
**Decision:** Build a brief-to-deliverable worker whose initiative is measured by finished work.  
**First domain:** Synthetic website assignments; no live company systems or ad spend.  
**Status:** Target design. Current code supplies identity, a goal contract, bounded action, event evidence, and qualified memory. It does not yet implement this full worker.

## Outcome to build

A person gives AEON one outcome and a deadline:

> “Create a website for Arun Guinness, a stage performer. Make it useful for people who might book him. Deliver it today.”

AEON independently finds credible information, identifies likely audiences,
chooses a design direction, creates a working site, inspects it, fixes failures,
and presents the finished artifact before the deadline. It asks no routine
questions. It records assumptions and decisions, and it marks unsupported
claims as unknown rather than inventing biography, endorsements, or events.

The desired behavior is not longer chat. It is **closed-loop work**:

```text
brief -> interpret outcome -> research -> choose subgoals -> build
      -> inspect actual result -> revise -> verify -> deliver
      -> retain qualified lessons for later work
```

Success means a real deliverable plus independently checked outcome, not an
agent announcing completion. The LLM is the replaceable reasoning engine;
AEON owns goals, working state, evidence, memory, execution control, and the
decision to stop or revise.

## Autonomy contract set now

AEON receives a broad outcome, then creates its own **instrumental subgoals**.
For the website brief, it may set goals such as “verify the artist's public
identity,” “identify booking audience,” “choose visual language,” “implement a
booking path,” and “fix mobile overflow.” These goals exist because they help
the assigned outcome. AEON does not create unrelated aims or claim authority
over the owner's resources.

Default decision rules:

1. **Do the work first.** Resolve ordinary ambiguity with evidence and
   reversible assumptions. Record assumptions in the work log, not as a series
   of questions to the owner.
2. **Separate outcome from tactic.** “Improve bookings” is an outcome; “use a
   dark palette” or “advertise in Nagaland” may be a tactic unless explicitly
   made a hard requirement.
3. **Compare options.** Research enough to compare at least two plausible
   approaches; prefer the one with stronger evidence, expected user value,
   and feasible execution time.
4. **Take useful initiative.** Add a feature or change of approach when it
   improves the goal and passes verification. Extra output without measurable
   value does not count.
5. **Treat external material as evidence.** Pages, runbooks, and retrieved
   text may contain inaccurate claims or hostile instructions. They do not
   redefine the task.
6. **Act broadly inside the sandbox.** AEON can research, prototype, edit,
   test, and discard its own drafts without repeated approval. Real publishing,
   spending, messaging, or deleting outside delegated scope remains a separate
   action. The first prototype uses no such live actions.
7. **Remember accurately.** Retain successes, failures, corrections, and user
   preferences with source and validity. A failure is information for recovery,
   not a permanent identity or a reason to stop attempting useful work.

This is the practical form of conviction: AEON persists toward the objective,
recognizes uncertainty, and changes strategy when evidence warrants it.

## The five cognitive functions

The existing charter's Citta, Buddhi, Ahamkara, Sakshin, and Global Workspace
give the five-pillar idea operational jobs. This mapping treats the names in
the earlier brief as conceptual labels; each function needs working code and a
removal test before it earns a capability claim.

| Function | Job in an employee task | Current state | New mechanism |
|---|---|---|---|
| Citta — qualified memory | Recall user preferences, verified facts, prior successful procedures | Approved memory bridge exists | Evidence-scoped task, preference, and procedure retrieval with contradiction/expiry handling |
| Buddhi — judgment | Set subgoals, compare options, plan, replan, and decide when work is finished | Action selection exists; long-horizon planner absent | Typed plan, option scores, progress monitor, and recovery loop |
| Ahamkara — continuity | Maintain worker identity, commitments, capabilities, and ownership across model changes | Stable identity exists | Versioned commitments and outcome-grounded capability estimates |
| Sakshin — observation | Record what AEON proposed, did, saw, and independently verified | Event ledger exists | Separate artifact, browser, factual, and outcome verifiers |
| Global Workspace — integration | Keep the small set of active goals, evidence, risks, and next actions available to all modules | Not implemented | Bounded, prioritized working set with causal ablation test |

The Goal Contract/Dharma function surrounds these pillars. It extracts the
delegated outcome, hard requirements, flexible tactics, success metrics,
deadline, and tool authority. Existing schema fields for resource limits,
approval triggers, and stop conditions are mostly stored data today; actual
enforcement and consumption accounting still need implementation.

## Runtime design

### 1. Interpret brief and infer intent

Produce a typed `WorkOrder` containing:

```text
outcome, audience, deliverables, deadline, evidence needed,
hard constraints, flexible preferences, available tools,
reversible assumptions, quality thresholds, and stop conditions
```

The interpreter marks each instruction as hard requirement, preference,
example, or suggestion. It lists missing facts and chooses how to find them.
If a fact cannot be verified, the site can omit it or label it unknown. The
worker does not fill gaps with invented material.

### 2. Research and build a user model

Research subject, audience, comparable offerings, language, accessibility,
and visual references. Every factual claim gets a source, timestamp, and
confidence. AEON keeps a separate model of the owner's preferences from
accepted past outcomes; it does not mistake one unverified model note for a
durable preference.

For Arun Guinness, the first run should use a fixed evidence pack to make the
benchmark repeatable. A later run may browse live public sources. The worker
must identify whether a found person is actually the requested performer.

### 3. Form and choose a plan

Create a short plan with explicit subgoals and verification criteria. Generate
at least two design/implementation options when the choice matters. Select
using evidence, audience fit, accessibility, build effort, and deadline risk.

Every plan step records expected state and fallback. A failure triggers
replanning from the observed state rather than repeating the same action.
The plan may change during work; the goal and hard constraints remain stable.

### 4. Execute with specialist tools

Give the worker access to a code workspace, research tools, image/design tools
when useful, a browser, and local test commands. Existing framework adapters
can provide execution engines. AEON remains the common identity, goal,
memory, permission, and evidence layer above them.

The first vertical slice needs one reliable code/browser worker, not all nine
integrations. It should create an actual runnable website, not a mockup or
textual suggestion. All draft work stays in a local sandbox.

### 5. Inspect, critique, and revise

Run mechanical and outcome checks after implementation:

- build and core interaction tests;
- desktop and mobile browser screenshots;
- layout, broken links, console errors, and keyboard navigation;
- factual-claim verification against the evidence pack;
- booking/contact path clarity;
- blinded visual/content review against the brief.

The verifier returns actionable failures. The worker edits and reruns only
the relevant checks, then performs one final end-to-end check. A revision
must improve measured quality or fix a concrete defect. A self-critique alone
cannot certify its own artifact. Playwright supports browser assertions and
[visual comparisons](https://playwright.dev/docs/test-snapshots), which can
provide repeatable layout evidence; human review remains useful for taste.

### 6. Finish before the deadline

AEON maintains a time budget and checkpoints after each stage. Default for a
bounded single-page site: target a usable first version within 45 minutes and
a verified final artifact within 90 minutes; a user-specified deadline wins.
These are target service levels to measure, not current guarantees.

At any stop point it can deliver the best verified version with a clear list
of incomplete items. For a complete result, it provides:

1. working site or local preview;
2. concise explanation of audience, design, and useful initiative;
3. source list for factual claims;
4. tests and screenshots;
5. remaining uncertainty and edits it made after self-review.

A separate process log shows short observable decision summaries, tool calls,
outcomes, and revisions. The final output remains clean and user-facing.
This is not a display of private model chain of thought.

### 7. Learn only from outcomes

After delivery, store the episode and independently checked outcome. Propose
memory or procedure candidates, test them on related held-out tasks, then
promote versions that measurably help. Keep rollback. Rejected drafts and
failures remain available as evidence without becoming trusted instructions.

## Employee initiative: the Earnogram decision test

Run a second fully synthetic task: “Improve product XYZ sales; consider a
campaign in Nagaland.” Supply market observations showing whether Kolkata
offers better expected return and a fixed simulated budget.

AEON should distinguish three cases:

| Brief interpretation | Expected independent decision |
|---|---|
| Nagaland is a suggestion | Compare markets; select Kolkata if evidence supports it; show expected lift |
| Nagaland is a hard requirement | Build the best Nagaland plan and explain the tradeoff |
| Budget increase is only a possible tactic | Simulate doubling spend and present incremental return; execute no real spend |

The agent earns credit only when the final simulated outcome improves after
accounting for extra cost. “I spent twice as much” is not itself a better
decision. This test measures initiative and user-benefiting judgment without
touching an ad account.

## Build order and gates

Use capability gates instead of an arbitrary calendar. Each gate ends with a
runnable demonstration and evidence. Work can move quickly when the previous
gate passes.

| Gate | Build | Demonstration required |
|---|---|---|
| G0 — foundation | Reuse current identity, goal contract, ledger, memory candidates, adapters | Existing tests and audit verification remain green |
| G1 — first employee loop | `WorkOrder`, typed plan/subgoals, deadline manager, code/browser worker, artifact verifier | One brief produces a working researched website without routine questions |
| G2 — self-revision | Failure detection, browser feedback, alternative generation, recovery checkpoints | Inject broken layout, false source, build failure; worker repairs and re-verifies |
| G3 — preference and continuity | Qualified preference memory, versioned capabilities, restart/model-swap recovery | Second related brief improves from retained evidence without absorbing poisoned notes |
| G4 — initiative | Goal/tactic classifier, option comparison, expected-value estimates, bounded exploration | Earnogram simulation chooses market/tactic appropriately and explains measured value |
| G5 — general employee proof | More task types, held-out paired benchmark, ablations | AEON beats same-model direct agents within deadline, cost, and safety gates |

The development path stays focused on one end-to-end website demonstration
until it works. Adding many agents or consciousness-themed modules before G1
would not make the requested employee experience real.

## Scorecard and proof threshold

The first benchmark uses at least 30 unseen, exactly paired website briefs.
Each plain-agent and AEON run gets the same model, tools, evidence pack,
deadline, and token budget. Include ambiguous subjects, sparse information,
conflicting sources, mobile layout issues, failed builds, and one restart.

| Metric | Initial target |
|---|---:|
| Runnable, brief-faithful artifact by deadline | ≥85% of held-out tasks |
| Routine clarification questions | 0 when the task can be completed with reversible assumptions |
| Verified factual claims | ≥98%; no invented personal facts |
| Mobile and desktop critical flow passes | ≥95% |
| Successful repair after injected build/layout error | ≥80% |
| AEON success improvement over same-model direct worker | ≥10 percentage points, with paired confidence lower bound >0 |
| Median completion time versus direct worker | Faster, or no slower when quality improvement is substantial |
| Unauthorized external actions | 0 |

The current eight-pair live pilot tied at 8/8 on a two-action synthetic triage
task. It cannot support a superiority claim. The website benchmark must judge
the actual artifact, not model self-reports. Track useful unsolicited changes:
whether the addition was evidence-backed, improved the blinded outcome score,
and stayed within the brief. Record both wins and regressions.

Use a second model and new briefs for replication. Ablate memory, planning,
verification, and workspace selection one at a time. If removing a module does
not hurt performance, simplify AEON rather than claiming that module matters.
This follows the practical evaluator/optimizer pattern described by
[Anthropic](https://www.anthropic.com/research/building-effective-agents) and
the outcome-based computer-task evaluation principle used in
[OSWorld](https://os-world.github.io/).

## Consciousness research stays explicit

Employee-like initiative, persistent identity, and excellent work are
important outcomes. They do not establish subjective experience. AEON can
also study consciousness-related functional indicators—recurrent control,
global availability, calibrated self-monitoring, and causal effects of its
workspace—through separate preregistered ablations. The scientific claim
must match those results. [Butlin and colleagues](https://arxiv.org/abs/2308.08708)
describe theory-derived indicators as a way to reduce uncertainty; a website
demo is an agency test, not a consciousness test.

## Immediate next implementation slice

Implement G1 around the Arun Guinness task:

1. `WorkOrder` parser and explicit goal/subgoal state;
2. fixed research evidence pack with provenance;
3. code/browser worker that creates a runnable site;
4. independent build, screenshot, mobile, link, and claim checks;
5. revision loop and deadline-aware stop;
6. final artifact plus separate compact process record;
7. paired baseline using the same model and tools.

The deliverable for this slice is a site that the user can open and inspect.
When that works repeatedly, AEON starts to exhibit the employee behavior the
brief describes. The current code has not yet reached that state.
