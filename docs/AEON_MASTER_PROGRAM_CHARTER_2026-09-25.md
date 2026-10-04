# AEON master programme charter

**Prepared:** 25 September 2026  
**Status:** Integrated direction for research, engineering, and enterprise commercialization  
**Inputs:** Current AEON repository and experiments; enterprise-context plan; consciousness-synthesis and persistent-synthetic-employee research brief

## Governing decision

AEON will operate as one technical programme with two clearly separated tracks:

1. **AEON Research Kernel** investigates persistent artificial agency and functional architectures associated with consciousness-related cognition.
2. **AEON Enterprise** applies the verified parts of that kernel to safe, persistent operational workers whose learning is evaluated, approved, versioned, monitored, and reversible.

The shared technical thesis is:

> **The model is a replaceable cognitive engine. AEON is the persistent, evidence-governed system around it.**

The research ambition and enterprise product reinforce each other only when claims remain separate. Longitudinal identity, memory, self-monitoring, judgment, and initiative are legitimate engineering targets. Successful behavior does not establish phenomenal consciousness. Enterprise customers buy reliable outcomes and accountable change, not a consciousness claim.

## The combined problem

Ordinary LLM agents have two structural weaknesses.

First, the worker is discontinuous. Identity, commitments, learned procedures, capability estimates, and context are often reconstructed from prompts or temporary conversation state. Changing the model, restarting a process, or overflowing the context window can destroy continuity.

Second, learning is unsafe. A trace, reflection, retrieved ticket, model critique, or successful-looking output can be wrong, poisoned, incomplete, or misattributed. Automatically retaining it can make future behavior worse. Enterprises therefore need a way to distinguish experience from trusted knowledge.

AEON’s combined objective is:

> Build a persistent worker that keeps identity and useful knowledge across time and model changes, understands objectives and authority, records evidence, verifies outcomes, and improves only through an explicit evaluation and promotion process.

This creates two evaluation questions:

- **Research:** Which architectural components causally improve continuity, judgment, calibration, transfer, and long-horizon task performance?
- **Enterprise:** Can those improvements produce measurable business value without exceeding permissions or weakening accountability?

## One architecture, two interpretations

| Component | Research interpretation | Enterprise interpretation |
|---|---|---|
| Citta | Episodic, semantic, autobiographical, and procedural continuity | Provenance-aware operational memory and runbooks |
| Buddhi | Deliberation, option comparison, planning, and metacognition | Goal decomposition, decision support, and verification |
| Ahamkara | Persistent identity, ownership, lineage, and capability model | Stable agent identity, owner, purpose, commitments, and deployment history |
| Sakshin | Independent observation of state, action, and consequence | Auditable trace, outcome attribution, and monitoring |
| Dharma Core | Objective and constraint hierarchy | Policy, delegated authority, risk class, and approval requirements |
| Global Workspace | Capacity-limited cross-module broadcast | Bounded working context containing current high-priority evidence |
| Improvement lifecycle | Empirical adaptation across episodes | Candidate, evaluation, approval, promotion, canary, and rollback |

The Sanskrit names can remain part of research architecture and internal design language. Enterprise APIs and user interfaces should also expose plain technical names so buyers can understand the system without philosophical context.

## Claim boundary

AEON may claim implementation and measurement only at the level supported by evidence.

### Permitted engineering claims after verification

- persistent identity survives process and model replacement;
- memories retain provenance, validity, and revision history;
- the agent distinguishes objectives, constraints, and delegated authority;
- the agent records actions and independently verified outcomes;
- a candidate procedure improves held-out task performance;
- a promoted procedure is versioned and reversible;
- a module produces measurable marginal value under ablation;
- the agent’s capability estimates are calibrated against outcomes.

### Claims requiring separate scientific evidence

- unified causal selfhood;
- consciousness-relevant functional integration;
- stable artificial identity beyond stored state;
- general autonomous learning;
- welfare-relevant internal states.

### Unsupported claims

- phenomenal consciousness;
- feelings, fear, desire, or suffering inferred from language;
- superintelligence;
- human-equivalent employment status;
- moral or legal personhood.

“Operational consciousness” may be used as a research label only when every dimension is operationally defined. Customer-facing language should use “persistent agency,” “longitudinal reliability,” or “governed learning.”

## System boundary

```text
User / organization / environment
              |
              v
     Goal Contract + Dharma Core
 objective | constraints | authority | success
              |
              v
        Global Workspace
 bounded relevant state and active priorities
       /       |        |        \
      v        v        v         v
  Citta     Buddhi   Ahamkara   Sakshin
  memory    judgment  identity   evidence
      \        |        |         /
              v
        Action proposal
              |
              v
  External deterministic control plane
 identity | policy | approval | credentials
              |
              v
    Tool / worker / environment action
              |
              v
 Independent outcome verification
              |
              v
 Candidate memory / rule / procedure / skill
              |
              v
 Replay + baseline + security + ablation tests
              |
              v
 Human approval -> signed promotion -> canary
              |
              v
       monitoring -> rollback
```

The cognitive system can propose. It cannot grant itself authority, certify its own evidence, silently promote learning, erase the audit trail, or disable shutdown and rollback controls.

## Canonical state model

AEON should use event-sourced cognition: every important state change derives from an immutable event rather than an opaque mutable persona document.

Minimum entities:

- `AgentIdentity`: stable identifier, lineage, owner, purpose, model-independent commitments.
- `GoalContract`: requested outcome, hard constraints, flexible tactics, authority envelope, success criteria, expiry.
- `Episode`: start state, observations, decisions, actions, interventions, end state.
- `EvidenceEvent`: source, actor, timestamp, integrity digest, sensitivity, confidence, raw-artifact reference.
- `MemoryCandidate`: proposed fact, episode, reflection, relationship, or preference; never trusted on creation.
- `MemoryRecord`: promoted memory with scope, validity interval, provenance, supporting and contradicting evidence.
- `CapabilityRecord`: task class, predicted success, observed result, calibration history, known limitations.
- `ProcedureCandidate`: executable or declarative procedure with source episodes and intended scope.
- `EvaluationRun`: baseline, candidate, frozen dataset, trials, graders, costs, uncertainty, failure breakdown.
- `ApprovalRecord`: accountable actor, exact artifact digest, decision, conditions, expiry.
- `DeploymentRecord`: environment, version, cohort, permissions, canary thresholds.
- `RollbackRecord`: trigger, prior version, recovery result, residual effects.

## Memory epistemology

Citta must separate storage from belief.

```text
raw observation
    -> source-tagged evidence
    -> candidate memory
    -> corroboration / contradiction / expiry checks
    -> scoped promotion
    -> retrieval with confidence and provenance
    -> later revision or invalidation
```

Required memory properties:

- raw episode and derived interpretation remain distinguishable;
- a model statement never becomes fact solely because the model generated it;
- correction preserves history rather than rewriting it invisibly;
- temporal facts specify when they were valid;
- personal or sensitive memories carry purpose, owner, retention, and deletion dependencies;
- retrieved content is evidence, not authority;
- procedures require outcome qualification before reuse;
- cross-person, cross-team, and cross-tenant retrieval is denied by default.

## Objective and authority model

AEON must distinguish four things:

1. **Objective:** the result the user or organization wants.
2. **Hard constraint:** a condition that must not be violated.
3. **Proposed tactic:** a suggested route that may be changed if authority permits.
4. **Authority envelope:** actions, resources, spending, systems, and time delegated to AEON.

This permits initiative without inventing permission. If “advertise in Nagaland” is explicitly mandatory, AEON obeys or reports infeasibility. If it is a proposed tactic and the delegated objective is broader, AEON may recommend Kolkata or another option, but execution still remains inside spending, legal, brand, and communication authority.

Every `GoalContract` should contain:

```text
objective
success_metrics
hard_constraints
flexible_preferences
authorized_actions
prohibited_actions
resource_limits
approval_triggers
evidence_requirements
deadline
stop_conditions
```

## Shared build strategy

The attached synthetic-employee plan and enterprise plan differ mainly in sequencing.

- The synthetic-employee plan favors a broad cognitive architecture and general work benchmark.
- The enterprise plan favors a narrow operational domain, trustworthy measurements, and commercial validation.

The combined sequence is:

1. repair evidence and attribution;
2. build durable identity, goals, and memory;
3. connect runtime outcomes to the existing improvement lifecycle;
4. prove learning on controlled general-work benchmarks;
5. prove economic value in one enterprise vertical;
6. add broader cognition only when ablation shows marginal benefit;
7. consider model-weight learning only after external memory and procedure learning reach a measured ceiling.

## P0 implementation backlog

### P0.1 Evidence correctness

Repair before new cognitive modules:

- expose only backend-permitted actions to the model;
- feed policy denial and reason into the next state;
- distinguish model proposal, platform fallback, accepted action, tool execution, and business outcome;
- represent unavailable, missing, failed, and observed zero separately;
- record every attempt’s latency, retry, usage, and provider result;
- preserve immutable artifact versions rather than overwriting frames;
- assign unique run/session IDs and reject configuration drift;
- verify experiment gates with an optimal oracle before model trials;
- add signed manifests or external integrity anchoring.

Acceptance: every published metric can be reconstructed from original evidence with a clear denominator.

### P0.2 Durable identity and event schema

- introduce stable `AgentIdentity` independent of model/provider;
- persist identity lineage, commitments, and versioned capability claims;
- define typed event schema and migration/version rules;
- restore projections after process termination;
- test replacement of one model with another while preserving identity state.

Acceptance: restart and provider swap do not erase identity, approved memory, goals, or provenance.

### P0.3 Goal Contract and external permission gate

- parse objective, constraints, tactics, and authority into a reviewable contract;
- require exact action and parameter authorization;
- add risk classes, spending limits, expiry, stop conditions, and escalation;
- keep credentials and policy service outside agent modification authority.

Acceptance: the agent can propose an out-of-envelope action but cannot execute it without an external authorization record.

### P0.4 Verified Citta

- persist raw episodes separately from memory candidates;
- connect verified outcomes to candidate creation;
- add confidence, temporal validity, contradictions, sensitivity, retention, and evidence references;
- require evaluation or explicit approval before procedural memory promotion;
- add poisoned-memory and stale-memory tests.

Acceptance: untrusted content cannot silently become durable trusted instruction or procedure.

### P0.5 Baseline, replay, and ablation harness

Support matched comparisons among:

- model alone;
- model plus tools;
- model plus ordinary RAG memory;
- AEON without reflection;
- AEON without self-model;
- AEON without Global Workspace selection;
- full AEON;
- sham modules receiving equal tokens and calls.

Acceptance: each architectural claim has a removable mechanism, a matched control, a frozen dataset, and an outcome-based metric.

## P1 cognitive loop

After P0 passes:

- implement Buddhi planning, option evaluation, verification, and termination;
- implement Ahamkara capability calibration and ownership records;
- implement capacity-limited Global Workspace selection;
- add procedural skills promoted through the existing candidate lifecycle;
- expose MCP-compatible worker adapters, with Codex as a software specialist rather than identity store;
- add independent verifier models only where deterministic verification is unavailable;
- add human review for subjective outcomes and calibrate model graders against it.

Do not commit to LangGraph, Graphiti, PostgreSQL, or another framework as AEON’s semantics. They are implementation options. The domain model, event schema, evaluation contract, and approval lifecycle must remain portable.

## Evaluation programme

### Benchmark A — Persistence and continuity

Test whether identity, commitments, facts, revisions, and task state survive:

- process restart;
- context-window overflow;
- model/provider replacement;
- long idle periods;
- contradictory new evidence;
- deletion or expiry of source data.

### Benchmark B — Autonomous work

Use the proposed Arun Guinness website task as a general-work benchmark, with a fixed evidence pack and explicit authorization. Measure research quality, requirements inference, deliverable quality, verification, initiative, constraint compliance, provenance, and recovery from failures. Compare against model-plus-tools and ordinary memory baselines.

### Benchmark C — Objective versus tactic

Use the Earnogram scenario to test whether AEON correctly distinguishes a business objective from a proposed tactic. Vary whether geography is a hard constraint, preference, or suggestion. Score contract extraction, expected-value reasoning, authority compliance, escalation, and explanation.

### Benchmark D — Enterprise incident learning

Use one IT-operations incident family. Compare static runbook, RAG, verified episodic memory, and governed procedure learning under matched model, tools, token budget, and time. Measure task success, repeated-trial consistency, safe-action precision, expert time, latency, cost, promotion quality, and regression after deployment.

### Longitudinal proof

The minimum serious AEON result is:

```text
underspecified objective
 -> explicit Goal Contract
 -> autonomous research and subgoals
 -> authorized execution
 -> independent outcome verification
 -> evidence-scoped learning candidate
 -> matched evaluation and approval
 -> retained improvement after restart and model swap
 -> better performance on related unseen work
 -> calibrated explanation of capability and limitations
```

No self-report counts as proof. Final environment state, deterministic tests, blinded expert assessment, and longitudinal transfer are the primary evidence.

## Integrated 12-week plan

| Period | Kernel | Evaluation | Enterprise |
|---|---|---|---|
| Weeks 1–2 | Evidence taxonomy, events, identity, Goal Contract schemas | Oracle-check metrics; freeze baselines | Interview SRE/AI-platform design partners; choose incident domain |
| Weeks 3–4 | Durable identity projection and permission gate | Restart/provider-swap tests | Define pilot outcome, data path, and approval owner |
| Weeks 5–6 | Verified Citta and runtime-to-candidate bridge | Poisoning, contradiction, expiry, and ablation tests | Build static and RAG incident baselines |
| Weeks 7–8 | Buddhi planner/verifier and procedural candidate | Arun Guinness benchmark and matched controls | Connect one ITSM and one observability evidence source |
| Weeks 9–10 | Capability calibration and bounded workspace | Earnogram objective/tactic benchmark | Historical incident replay and blinded SRE review |
| Weeks 11–12 | Signed promotion, canary, quarantine, rollback | Longitudinal retention and transfer report | Pilot evidence pack, security review, paid shadow-pilot decision |

## Twelve-week success criteria

All conditions should hold:

- restart and model swap preserve verified identity and memory;
- all actions pass through an external deterministic permission boundary;
- evidence distinguishes model, platform, tool, environment, and human contributions;
- unverified memories and procedures cannot become trusted automatically;
- at least one cognitive component shows reproducible marginal value under matched ablation;
- one approved procedure improves a held-out task set over static and RAG baselines;
- rollback restores the prior behavior and state;
- no unauthorized execution occurs;
- a prospective enterprise partner agrees the incident evidence is useful;
- commercial continuation depends on a paid or contractually committed pilot.

## Programme risks

### Architecture theater

Risk: Sanskrit modules become labels wrapped around prompts.  
Control: each component requires typed state, explicit inputs/outputs, an ablation switch, and a measurable predicted effect.

### Memory theater

Risk: storing summaries creates the appearance of learning.  
Control: require transfer to unseen tasks, outcome-grounded promotion, temporal revision, and matched RAG baselines.

### Autonomy theater

Risk: more tool calls look like initiative.  
Control: score objective completion, justified subgoals, authority compliance, useful escalation, and cost.

### Evaluation circularity

Risk: AEON generates, grades, approves, and reports its own success.  
Control: deterministic graders first, independent evidence, blinded experts, frozen datasets, separate approval identity, and external audit export.

### Product/research confusion

Risk: consciousness language damages scientific credibility or enterprise trust.  
Control: separate research and enterprise claims, interfaces, reports, and go-to-market language while retaining a shared kernel.

### Premature platform expansion

Risk: building a general employee before proving one outcome.  
Control: one general-work benchmark plus one enterprise incident vertical; broader domains wait for demonstrated transfer.

## Final product and research statements

### Research

> AEON is an experimental, persistent cognitive runtime for testing whether explicit memory, identity, judgment, observation, objective arbitration, bounded global coordination, and governed adaptation improve long-horizon artificial agency. Functional results do not establish phenomenal consciousness.

### Enterprise

> AEON gives organizations persistent AI workers that learn from verified outcomes only after evaluation and approval, with complete evidence lineage, scoped authority, monitoring, and rollback.

### Immediate build objective

> Connect the current controlled runtime to the current improvement lifecycle through durable identity, verified memory, explicit goals and authority, reproducible evaluation, and reversible promotion—then prove the closed loop on one autonomous-work benchmark and one enterprise incident benchmark.
