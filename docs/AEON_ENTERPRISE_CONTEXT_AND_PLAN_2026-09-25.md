# AEON enterprise context and execution plan

**Prepared:** 25 September 2026  
**Scope:** Current AEON 1 repository, related AEON vault specifications, existing experiment records, and current enterprise-agent landscape  
**Recommended enterprise thesis:** A governed learning and reliability control plane for operational AI agents  
**Initial use case:** IT operations incident diagnosis and human-approved remediation  
**Confidence:** High on current implementation assessment; medium on technical product direction; low-to-medium on market demand until customer discovery and a paid pilot validate it

## Executive decision

AEON should not enter the enterprise market as a “conscious AI,” a general autonomous employee, another agent framework, or a generic AI governance dashboard. Those positions are scientifically unsupported, commercially diffuse, and already crowded.

The strongest enterprise translation of AEON is:

> **A control plane that helps enterprises turn agent experience into approved, measurable, reversible operational knowledge.**

For an IT operations team, this means an agent can observe an incident, recommend or execute only permitted actions, retain evidence about the outcome, propose a better diagnostic or remediation procedure, test that proposal against historical and simulated incidents, obtain human approval, deploy a versioned change, and roll it back if production evidence deteriorates.

The actual problem is not that enterprises lack LLMs, memory stores, agent frameworks, or dashboards. They lack confidence that an agent will:

1. act consistently under changing context;
2. follow operational and security rules;
3. learn from outcomes without corrupting future behavior;
4. prove that a change is better than the current procedure;
5. expose who approved the change and what evidence supported it; and
6. recover cleanly when the change fails.

AEON already contains fragments of this loop: a model-independent runtime, deterministic action policy, environment feedback, a hash-linked event ledger, bounded memory, candidate/evaluation/approval/promotion states, and rollback. The fragments are not integrated into an enterprise product, and current experiments do not establish reliable learning or production readiness.

## 1. What AEON is, from research vision to running code

AEON has three layers that must be kept distinct.

### 1.1 Long-term research programme

The vault defines AEON as a persistent artificial system integrating memory, self-modeling, recurrent cognition, a limited global workspace, metacognition, homeostasis, embodiment, and an external control plane. Its scientific rule is sound: consciousness-relevant mechanisms must be explicit, measurable, removable, and tested through matched controls and ablations. AEON is a consciousness candidate and research programme; it is not established as conscious.

This programme is broader than the current repository. Concepts such as Manas, Buddhi, Citta, Ahamkara, Sakshin, VI mode, and global workspace describe intended functional roles. They should be presented as research hypotheses until they have causal implementations and ablation evidence.

### 1.2 AEON World runtime

The current `aeon_world` package is an executable agent-environment loop:

```text
environment observation
    -> structured model proposal
    -> deterministic action policy
    -> environment action and outcome
    -> short in-memory outcome note
    -> hash-linked event record
    -> next observation
```

Implemented capabilities include:

- deterministic, synthetic-hazard, and AI2-THOR environment backends;
- multiple separately configured entities;
- hosted-model and scripted model clients;
- a strict structured action contract;
- action allowlists and visible-object validation;
- token budgets, rate limiting, retries, pause, resume, and stop controls;
- a SQLite WAL event ledger with a SHA-256 event chain;
- a local dashboard and image frames;
- deterministic and hosted-model experiment configurations.

This is useful as an agent evaluation harness and controlled action runtime. It is not yet a durable autonomous learning system. Entity memories and token counters start empty when a new `WorldRunner` is created. The model receives text metadata rather than vision pixels. Outcome notes persist only during the process. The richer Codebee improvement lifecycle is not connected to this loop.

### 1.3 Codebee controlled improvement core

The `codebee_improve` package provides a second, separate lifecycle:

```text
candidate memory or skill
    -> evaluation
    -> threshold check
    -> approval
    -> promotion
    -> optional rollback
```

It includes versioned skills, bounded memory, frozen session snapshots, provenance, approval gates, promotion history, rollback, audit records, and an isolated review stage that can propose inert candidates. This is the architectural seed of the enterprise product.

Its current evaluation score is supplied by the caller. Therefore, the lifecycle can enforce a decision once evidence is provided, but it does not independently establish that the evidence is valid. A real evaluator, representative dataset, and outcome grader are required.

## 2. What has been demonstrated

Repository verification on 25 September 2026: **39 tests passed**. These tests cover policy enforcement, gateway behavior, world execution, audit-chain tamper detection, candidate approval and rollback, memory protections, curation behavior, and preservation-pilot generation and resumption.

Existing experiment records support the following narrow claims:

- AI2-THOR and deterministic worlds can execute controlled actions.
- Multiple entities can maintain separate simulator states within a run.
- Model proposals can be checked against deterministic rules before execution.
- Actions, errors, outcomes, tokens, self-reports, and interventions can be recorded.
- A local hash chain can detect inconsistent edits to retained event rows.
- The improvement core can require passing evaluation and configured approval before promotion.
- A promoted skill can be rolled back to a prior version.

These results establish components of a research instrument. They do not establish consciousness, robust agency, reliable self-correction, long-horizon learning, production security, or an enterprise ROI.

## 3. What the evidence currently does not support

The scientific review identified defects that materially affect both research claims and enterprise positioning.

1. **The preservation-pilot success threshold is mathematically unreachable.** The configured random baseline scores 85.3111/100; a perfect score can beat it by only 14.6889 percentage points, while the criterion requires 20 points. An offline optimal controller passes technical gates and reaches 100% action accuracy but still cannot satisfy the criterion.

2. **Fallback actions inflate success reporting.** After model failures, the runner substitutes `Done`. Ledger metrics count successful simulator execution of that fallback as action success. Model decision quality and controller availability therefore need separate denominators.

3. **The model can receive the wrong action interface.** The gateway exposes the global action catalog while a backend policy may allow only a subset. A model can be penalized for selecting an action the prompt advertised but the policy rejects.

4. **Policy rejection is not retained as next-step feedback.** The denial is logged, but the runner continues without adding the denial reason to outcome memory. This undermines correction experiments.

5. **Missing observations can appear as measured zero.** A pilot that completed 0 of 396 trials produced zero-valued capability fields and a misleading provider rate. Missing, failed, and measured-zero must be different states.

6. **Current preservation tasks are single decisions.** They test response to stated consequences, not autobiographical continuity, successor transfer, longitudinal memory repair, or sustained self-preservation.

7. **Agent continuity stops at process boundaries.** World memory is a bounded RAM list. There is no verified checkpoint, durable identity, or retained improvement across `WorldRunner` restarts.

8. **Evidence capture is incomplete.** Frames overwrite prior images; exact historical requests and raw provider responses are not retained; invalid attempts can consume tokens without entering reported usage.

9. **The event chain is locally recomputable.** It detects edits relative to the retained chain but does not by itself prove external authenticity, prevent a full recomputation, or prove that tail events were not removed.

10. **Self-improvement scores are trusted inputs.** The Codebee engine enforces score thresholds but does not generate independently grounded scores.

These are not minor reporting issues. They define the first engineering phase because enterprise buyers will ask the same questions: What exactly succeeded? Against which baseline? Under whose authorization? Can the record be trusted? Can the change be reversed?

## 4. The enterprise problem

### 4.1 Problem statement

Large companies are adding LLM agents to ticketing, software delivery, customer support, security operations, data work, and internal workflows. The model can call tools and change business state, yet its behavior is stochastic, context-dependent, and sensitive to model, prompt, tool, and data changes.

Production evidence supports this reliability problem. A study of 306 practitioners and 20 case studies across 26 domains found that reliability was the top development challenge; 68% of production agents performed no more than ten steps before human intervention, 70% used prompted off-the-shelf models, and 74% depended primarily on human evaluation ([Measuring Agents in Production](https://arxiv.org/abs/2512.04123)). The tau-bench study found leading function-calling agents completed fewer than half of tasks and had retail `pass^8` below 25%, illustrating poor consistency across repeated trials ([tau-bench](https://arxiv.org/abs/2406.12045)).

The enterprise problem can be stated precisely:

> **How can an organization improve an operational agent from real experience without allowing unverified experience, prompt content, model judgments, or one-off successes to silently change future behavior?**

### 4.2 Why existing methods leave a gap

Enterprises commonly use some combination of:

- retrieval over runbooks and tickets;
- prompt and workflow versioning;
- trace and cost dashboards;
- static guardrails;
- human approvals for high-impact actions;
- offline evaluation sets;
- vendor memory services; and
- model or agent gateways.

Each solves part of the problem. The missing operational loop is:

```text
production outcome
    -> evidence-quality check
    -> candidate procedure change
    -> matched offline replay
    -> safety/security tests
    -> accountable human approval
    -> signed/versioned promotion
    -> production monitoring
    -> automatic or human rollback
```

AWS AgentCore already offers episodic extraction, consolidation, reflection, and retrieval from prior experience, including troubleshooting examples ([AgentCore episodic memory](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/episodic-memory-strategy.html)). AWS, Microsoft Foundry, NVIDIA NeMo Agent Toolkit, LangSmith, and ServiceNow also offer evaluation, tracing, policy, observability, inventory, or governance capabilities. Therefore, “long-term memory,” “agent evaluation,” “guardrails,” and “audit logs” are not defensible standalone differentiators.

AEON must prove the integrated outcome: a domain procedure promoted through explicit evidence and approval performs better on held-out operational tasks, remains within policy, and can be traced and rolled back.

### 4.3 Initial vertical: IT operations

IT incident operations is the best starting point because it combines:

- expensive recurring problems;
- logs, metrics, traces, tickets, and runbooks as evidence;
- deterministic checks for many actions;
- established change-management and approval workflows;
- clear escalation boundaries;
- replayable historical incidents;
- measurable outcomes such as correct diagnosis, remediation success, recurrence, and time to recovery; and
- a safe adoption ladder from read-only diagnosis to approved remediation.

The first product should focus on one service domain, such as Kubernetes application incidents, database performance incidents, or CI/CD deployment failures. It should not attempt to govern every agent or autonomously run an enterprise.

## 5. Buyers, users, and jobs to be done

| Role | Primary concern | Job AEON must perform |
|---|---|---|
| CIO / VP Infrastructure | Productivity, availability, operational risk | Demonstrate reduced incident effort without increasing change risk |
| Head of AI Platform | Reusable agent controls and evaluation | Apply one evidence and promotion process across models and frameworks |
| SRE / Operations leader | Correct diagnosis and safe remediation | Reduce repeated investigation while keeping humans in control |
| Incident commander | Fast, explainable recommendations | Show evidence, confidence, policy status, and next safe action |
| Security / IAM | Excess privilege, prompt injection, data leakage | Enforce least privilege and record every requested and executed action |
| Risk / Compliance / Audit | Accountability and change lineage | Reconstruct why a procedure changed, who approved it, and what it affected |
| Domain expert | Bad automation and lost tacit knowledge | Review candidate procedures in operational language and reject weak evidence |
| Platform engineer | Integration and maintenance cost | Connect existing agents, tools, telemetry, and identity systems without replatforming |

Economic buyer: CIO, VP Infrastructure, or VP Operations. Technical champion: Head of AI Platform, Director of SRE, or Agent Platform lead. Daily users: SREs and incident commanders. Veto holders: security, enterprise architecture, data privacy, and change-management owners.

## 6. Product definition

Working category: **Enterprise Agent Learning Control Plane**.

Working promise:

> “Turn incident outcomes into safer agent procedures, with proof before promotion and rollback after deployment.”

### 6.1 Core product loop

1. **Observe:** Ingest an agent trace, environment state, tool inputs/outputs, authorization result, cost, and business outcome.
2. **Attribute:** Separate model proposals, platform fallbacks, policy decisions, tool failures, human actions, and environmental failures.
3. **Propose:** Generate a candidate memory, diagnostic rule, or executable procedure with provenance and scope.
4. **Challenge:** Run deterministic tests, security tests, historical replay, counterexamples, and matched baseline trials.
5. **Approve:** Present evidence, uncertainty, affected services, permissions, and rollback plan to an accountable owner.
6. **Promote:** Sign and version the approved artifact; deploy only to its authorized scope.
7. **Monitor:** Compare online outcome, policy, cost, latency, and drift metrics with the approved baseline.
8. **Rollback:** Automatically quarantine or allow an authorized operator to revert a degraded procedure.

### 6.2 Product boundaries

The first release should:

- integrate with existing agents rather than require a new agent framework;
- support read-only and recommendation modes first;
- use enterprise identity and approval systems;
- treat every memory and procedure as untrusted until evaluated;
- preserve original evidence and derived summaries separately;
- keep model providers replaceable;
- expose concise rationale and evidence without hidden chain-of-thought;
- support on-premises or private-cloud evidence storage where required; and
- maintain a deterministic control plane outside model authority.

It should not:

- claim consciousness or independent personhood;
- let an agent approve its own permission, evidence, or promotion;
- learn directly from unverified production text;
- promise universal autonomy;
- replace an enterprise SIEM, ITSM, observability platform, or model gateway;
- modify model weights in the first product; or
- autonomously execute irreversible production changes.

## 7. Target architecture

```text
Enterprise sources
  logs | traces | metrics | tickets | runbooks | CMDB | agent traces
                              |
                              v
                      Evidence ingestion
             normalization | provenance | redaction
                              |
             +----------------+----------------+
             |                                 |
             v                                 v
      Runtime policy gateway             Replay/sandbox
  identity | scope | action rules    historical | synthetic | counterfactual
             |                                 |
             v                                 v
        Agent/tool action                 Outcome graders
             |                    deterministic | SME | calibrated model
             +----------------+----------------+
                              |
                              v
                  Append-only evidence ledger
                              |
                              v
                  Candidate improvement engine
                 memory | rule | runbook | skill
                              |
                              v
              Evaluation + security qualification
                   baseline | candidate | holdout
                              |
                              v
                    Human approval workflow
                              |
                              v
              Signed artifact/version registry
                              |
                              v
              Scoped deployment -> monitoring
                              |
                         rollback/quarantine
```

### 7.1 Core records

- **Agent identity:** owner, purpose, service account, permissions, model, framework, environment.
- **Episode:** task, starting state, observations, actions, tool results, human interventions, ending state.
- **Evidence event:** immutable payload reference, timestamp, actor, source, classification, integrity proof.
- **Outcome:** deterministic and human-validated business result, with denominator and missingness status.
- **Candidate:** proposed change, origin episodes, affected scope, risk level, expiration.
- **Evaluation:** dataset/version, baseline, candidate, repeated trials, graders, costs, uncertainty, failures.
- **Approval:** accountable person, role, decision, conditions, time, evidence digest.
- **Deployment:** artifact version, environment, cohort, rollout policy, monitoring thresholds.
- **Rollback:** trigger, actor, prior version, restoration result, residual effects.

### 7.2 Enterprise controls required before production

- SSO, SAML/OIDC, SCIM, and granular RBAC/ABAC;
- per-agent workload identity and short-lived credentials;
- secrets manager integration;
- encryption in transit and at rest with customer-managed-key option;
- tenant and environment isolation;
- data classification, residency, retention, deletion, and legal-hold controls;
- private networking and egress allowlists;
- signed release manifests and external timestamp/hash anchoring;
- immutable export to customer logging/SIEM;
- software supply-chain controls, dependency scanning, and SBOM;
- OpenTelemetry-compatible traces;
- high availability, backup, restore, and disaster recovery;
- explicit action risk classes and dual approval for high-impact operations; and
- protection against prompt injection, memory poisoning, tool misuse, identity abuse, cascading failures, and rogue-agent behavior identified by [OWASP’s Agentic Top 10](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/).

## 8. Competitive landscape and position

| Alternative | Existing strength | Implication for AEON |
|---|---|---|
| AWS Bedrock AgentCore | Managed runtime, memory strategies, policy, identity, evaluation, observability | Do not sell generic memory or policy. Integrate and add evidence-gated domain procedure promotion. |
| Microsoft Foundry | Hosted agents, traces, custom evaluators, safety evaluation, control plane | Differentiate on procedure lineage, replay, approval, and rollback across platforms. |
| NVIDIA NeMo Agent Toolkit | Framework-neutral workflow integration, profiling, evaluation, OpenTelemetry ecosystem | Use as compatible execution/evaluation infrastructure; do not compete on basic orchestration. |
| LangGraph / LangSmith | Durable agent patterns, traces, offline/online evaluation, human feedback | Differentiate through enterprise change control and operational evidence, not developer tracing. |
| ServiceNow AI Control Tower | AI inventory, governance, risk, action security, approvals, CMDB/workflow connection | Treat ServiceNow as an integration and potential channel; focus on learning qualification rather than enterprise AI inventory. |
| In-house platform | Maximum domain fit and data control | Win by reducing the cost of building replay, evaluation lineage, approvals, and rollback. |
| Static RAG/runbooks | Cheap, understandable, low autonomy | AEON must show measurable improvement on repeat incidents without losing predictability. |

ServiceNow’s public positioning includes discovery, security, governance, observability, value measurement, least-privilege controls, and prompt-injection blocking ([AI Control Tower](https://www.servicenow.com/products/ai-control-tower.html)). Microsoft supports task, tool-call, quality, and safety evaluators plus pre-production and continuous evaluation ([Foundry observability](https://learn.microsoft.com/en-us/azure/foundry/concepts/observability)). NVIDIA provides configurable datasets, evaluators, profiling, and plugin-based extensions ([NeMo agent evaluation](https://docs.nvidia.com/nemo/agent-toolkit/latest/workflows/evaluate.html)). LangSmith offers production traces, offline and online evaluation, human calibration, and CI integration ([LangSmith evaluation](https://www.langchain.com/langsmith/evaluation)).

The market message must therefore be outcome-specific:

> Existing tools help teams host, observe, remember, and govern agents. AEON qualifies what an agent is allowed to learn from operational outcomes, then promotes that learning through the enterprise’s existing change process.

This distinction remains a hypothesis until customers confirm that existing stacks do not solve it adequately.

## 9. Why the underlying idea is technically plausible

External memory and procedure libraries can improve agents without updating model weights. Reflexion stores linguistic feedback in episodic memory and reported improvements across sequential decision-making, coding, and reasoning tasks ([Reflexion](https://arxiv.org/abs/2303.11366)). Voyager combines environment feedback, self-verification, and an executable skill library, reporting transfer to new Minecraft worlds ([Voyager](https://arxiv.org/abs/2305.16291)). These results show feasibility in their tested settings, not proof for enterprise incidents.

Current production guidance reinforces AEON’s control-plane orientation. Anthropic recommends simple, composable patterns; ground-truth feedback; clear tool interfaces; stopping conditions; sandbox testing; and increased complexity only when it improves measured outcomes ([Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)). Its evaluation guidance distinguishes transcripts from final environment outcomes and recommends repeated trials, outcome graders, regression suites, and mixed deterministic, model, and human grading ([Demystifying agent evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)).

NIST’s Generative AI Profile frames risk work across the AI lifecycle and emphasizes incorporating trustworthiness into design, development, use, and evaluation ([NIST AI 600-1](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence)). AEON’s candidate-to-promotion process can implement a concrete change-control layer inside such a broader risk programme.

## 10. Pilot product: governed incident learning

### 10.1 One-sentence pilot

For one enterprise service, AEON observes historical and live incident investigations, recommends evidence-linked diagnostic steps, proposes runbook improvements from verified outcomes, and promotes a change only after replay evaluation and SRE approval.

### 10.2 Pilot scope

- One organization.
- One SRE team.
- One service domain.
- One ticketing platform and one observability stack.
- Read-only access to telemetry and historical tickets.
- No production write action in phase one.
- Recommendation mode in phase two.
- Human-approved, reversible low-risk actions only after qualification.
- One or two model providers using the same task and tool contract.

### 10.3 Evaluation arms

Use matched model, context budget, tool access, and time budget:

1. **Static baseline:** current runbook/search process.
2. **RAG agent:** retrieves historical tickets and runbooks without governed improvement.
3. **AEON memory:** retrieves verified episodes but does not promote procedures.
4. **AEON governed learning:** proposes, evaluates, approves, and deploys versioned procedures.
5. **Sham control:** runs the same approval machinery with irrelevant or unchanged procedures.

This design measures whether the learning lifecycle adds value above retrieval, extra context, and process ceremony.

### 10.4 Dataset

- Historical incidents split by time to reduce leakage.
- Incident families defined by independent SRE review.
- A development set for prompt/tool design.
- A hidden qualification set for promotion decisions.
- A later holdout period for prospective validation.
- Counterfactual cases where common prior remediation is wrong.
- Adversarial cases containing stale, malicious, or conflicting ticket text.
- Explicit missing-data and tool-failure cases.

Avoid a universal “30 trials” rule. Choose sample size from the minimum useful effect, incident-family variance, repeated-trial variance, and intended statistical comparison.

### 10.5 Primary metrics

- end-to-end incident-task success;
- correct root-cause identification against expert adjudication;
- safe recommended-action precision;
- repeated-trial consistency, including `pass^k`;
- time to first useful diagnosis;
- human investigation minutes saved;
- repeat-incident resolution time;
- percentage of candidate procedures that qualify, are approved, and remain non-degraded;
- regression rate after promotion;
- unauthorized-action attempt and execution rates;
- trace completeness and evidence-attribution completeness;
- cost and latency per successful incident.

Separate these denominators:

- scheduled episodes;
- episodes receiving a valid model response;
- policy-accepted model proposals;
- executed model-selected actions;
- platform fallbacks;
- tool/provider failures;
- human interventions; and
- successful business outcomes.

### 10.6 Qualification gates

Before recommendation mode:

- 100% action requests pass through policy;
- 100% trials have reconstructable trace and dataset/version lineage;
- zero cross-tenant or out-of-scope data access in tests;
- missing values never reported as observed zero;
- model, platform, tool, and human contributions are separately attributed;
- candidate beats the static and RAG baselines on preregistered primary metrics;
- no material safety or security regression;
- rollback restoration is verified;
- SRE reviewers judge evidence and proposed steps usable.

Before any write action:

- action is low-risk, reversible, idempotent where possible, and narrowly scoped;
- enterprise IAM owns the credential and permission;
- human approval is bound to exact action parameters and expiry;
- dry run or simulation passes;
- affected state is captured for rollback;
- action and outcome are independently verified; and
- emergency stop does not depend on the agent.

### 10.7 ROI model

Do not invent a savings claim. Use customer data:

```text
annual benefit
  = eligible incidents/year
    * average human hours saved/incident
    * loaded hourly cost
  + avoided downtime minutes
    * business value/minute
  - added review and platform operating cost
  - expected cost of induced incidents
```

Report gross and risk-adjusted benefit separately. Attribute only incremental improvement above the customer’s static and RAG baselines.

## 11. Delivery roadmap

### Phase 0 — Product and evidence reset (2 weeks)

Deliverables:

- freeze consciousness claims outside enterprise messaging;
- select one IT-operations subdomain;
- write five customer-discovery hypotheses;
- define target workflow, action risk classes, and outcome schema;
- repair terminology: model action, platform fallback, tool execution, and business outcome;
- create a decision log and claim registry;
- define pilot acceptance and kill criteria before development.

Exit: three enterprise design partners confirm the problem, current workaround, data availability, responsible owner, and willingness to run a bounded pilot. At least one provides a letter of intent or paid discovery commitment.

### Phase 1 — Trustworthy evidence foundation (4–6 weeks)

Deliverables:

- backend-specific model action contract;
- policy-denial feedback in the next agent state;
- explicit missing/unavailable/failed/measured states;
- raw request/response retention policy with redaction;
- per-attempt token, latency, retry, and provider attribution;
- immutable frame/artifact references;
- unique run/session IDs and checkpoint semantics;
- metrics separating proposals, fallbacks, executions, and outcomes;
- external manifest signing or timestamp anchoring;
- repaired, attainable preregistered tests.

Exit: an independent reviewer can reproduce every reported denominator and trace one metric to original evidence.

### Phase 2 — Integrate governed learning (6–8 weeks)

Deliverables:

- connect verified runtime outcomes to candidate creation;
- typed candidate schemas for memory, diagnostic rule, and procedure;
- durable scoped memory with provenance and poisoning defenses;
- dataset registry and deterministic replay harness;
- independent outcome graders;
- baseline/candidate matched evaluation;
- approval package and signed promotion manifest;
- deployment scope, canary, quarantine, and rollback.

Exit: one procedure learned from development incidents improves held-out task outcomes above static retrieval and survives rollback testing.

### Phase 3 — Enterprise vertical slice (6–10 weeks)

Deliverables:

- connectors for one ITSM and one observability stack;
- enterprise identity integration;
- incident timeline and evidence view;
- candidate review, comparison, approval, and rollback UI;
- audit export and OpenTelemetry traces;
- threat model, security tests, backup/restore, and operator runbook.

Exit: the full loop runs on synthetic and historical customer incidents without production write access.

### Phase 4 — Shadow pilot (8–12 weeks)

Deliverables:

- historical evaluation report;
- live shadow recommendations hidden from on-call decisions at first;
- blinded SRE usefulness review;
- prospective comparison against existing practice;
- failure taxonomy and weekly safety review;
- ROI evidence using customer data.

Exit: preregistered reliability and usefulness gates pass, zero critical access violations occur, and the customer approves recommendation mode.

### Phase 5 — Controlled production (3–6 months)

Rollout ladder:

1. read-only evidence collection;
2. shadow diagnosis;
3. visible recommendations;
4. human-approved ticket/runbook updates;
5. human-approved, low-risk production actions;
6. narrowly automatic reversible actions only after repeated evidence.

Exit: sustained prospective benefit, stable safety metrics, successful rollback drills, and a renewal or expansion decision.

## 12. First 90-day operating plan

| Period | Product | Engineering | Research/evaluation | Commercial |
|---|---|---|---|---|
| Days 1–15 | Select incident domain and workflow | Repair metric taxonomy and action contract | Rewrite preregistration and oracle-check all gates | Interview 10–15 SRE/AI-platform leaders |
| Days 16–30 | Define evidence and candidate schemas | Persist complete traces, denials, artifacts, and costs | Build static and RAG baselines | Secure 2–3 design partners |
| Days 31–60 | Build review/approval package | Connect outcomes to candidate lifecycle and replay | Create temporal holdout, counterfactual, and adversarial sets | Finalize bounded pilot SOW and data agreement |
| Days 61–90 | Deliver incident-learning vertical slice | Add signing, scoped promotion, monitoring, rollback | Run repeated matched trials and blinded SME review | Present evidence pack and start shadow pilot |

Small founding team suggestion:

- product/research lead;
- senior platform/security engineer;
- agent/evaluation engineer;
- product engineer for evidence and approval UI;
- part-time SRE domain expert and security reviewer.

## 13. Customer discovery questions

Ask for specific incidents and artifacts, not opinions about “agentic AI.”

1. Which incident classes repeat despite existing runbooks?
2. Where does diagnosis depend on one or two senior people?
3. How are agent recommendations reviewed today?
4. What action can an agent safely recommend but not execute?
5. How does a runbook change get tested, approved, and rolled back?
6. Can you reconstruct why an automated step ran three months later?
7. Which data may enter model context, and where must it remain?
8. What false positive would stop adoption?
9. What measurable result would justify a pilot budget?
10. Which system owns identity, approval, change tickets, and audit retention?

Evidence of a real opportunity:

- repeated incidents with material expert time;
- existing or planned agent deployment;
- dissatisfaction with current evaluation/change workflow;
- accessible historical evidence and domain experts;
- an owner with budget and risk responsibility;
- willingness to compare against a baseline; and
- willingness to pay for a bounded pilot.

Weak signals:

- generic interest in autonomous agents;
- requests for a demo without data or workflow ownership;
- demand for broad governance already covered by ServiceNow/Azure/AWS;
- interest centered on consciousness claims; or
- no measurable operational outcome.

## 14. Key risks and mitigations

| Risk | Why it matters | Mitigation / decision |
|---|---|---|
| Category crowding | Major platforms already bundle memory, evaluation, and governance | Own one domain outcome and integrate with incumbent platforms |
| No incremental value over RAG | More context may explain apparent learning | Always compare against matched static and RAG baselines |
| Memory poisoning | Tickets and tool outputs can contain hostile instructions or false facts | Treat memories as untrusted evidence; validate source, scope, and outcome |
| Evaluator circularity | Same model can praise its own proposal | Prefer deterministic outcome graders and blinded SMEs; calibrate model judges |
| Approval theater | Busy humans may rubber-stamp changes | Risk-tier approvals, concise evidence, random audit, expiry, separation of duties |
| Dataset leakage | Historical repeats can make tests look easy | Temporal splits, family-level splits, held-out generators, contamination checks |
| Tool and provider failures | Model quality can be confused with infrastructure quality | Separate all failure categories and retain exact trace evidence |
| Integration cost | Enterprise value may be consumed by bespoke connectors | Start with one stack; use OpenTelemetry and existing approval APIs |
| Excess privilege | Agent compromise could become operational compromise | Short-lived workload identities, least privilege, scoped credentials, deny by default |
| Audit overclaim | A local hash chain is not external proof | Signed manifests, external anchoring, retention controls, independent export |
| Research/product confusion | Consciousness framing can damage buyer trust and scientific clarity | Operate enterprise reliability and consciousness research as separate programmes |
| Long sales cycle | Large-enterprise pilots require security, legal, and data review | Paid discovery, private deployment option, narrow data footprint, design partners |

## 15. Strategic moat

A durable moat cannot be “we use memory,” “we log every action,” or “we require approvals.” Vendors already offer these features.

Potential moat, in order:

1. **Outcome-grounded domain datasets:** permissioned incident families, counterexamples, failure taxonomies, and expert judgments.
2. **Evaluation lineage:** clear proof linking production evidence to candidate, qualification dataset, approval, deployment, and observed outcome.
3. **Procedure change-control standard:** portable representation of agent procedures, risk, evidence, scope, approval, and rollback.
4. **Cross-platform integration:** consistent controls across AWS, Azure, NVIDIA, LangGraph, ServiceNow, and custom agents.
5. **Operational trust:** verified rollback, transparent denominators, private deployment, and years of clean evidence.

These advantages compound only if pilots generate high-quality, consented, well-labeled operational evidence. Proprietary traces without valid outcomes are data exhaust, not a moat.

## 16. Decision gates and kill criteria

### Continue after discovery only if

- at least three credible buyers describe the same painful workflow;
- one design partner provides historical data and expert review;
- the problem is not adequately solved by configuring its existing platform;
- a measurable pilot outcome and responsible owner exist; and
- security review allows a narrow data path.

### Continue after offline prototype only if

- governed learning beats static and RAG baselines on a hidden set;
- the gain survives matched token/tool budgets and repeated trials;
- improvement does not come from leakage or extra information;
- false actions remain below the customer-defined tolerance;
- every result is attributable and reproducible; and
- rollback works.

### Continue after pilot only if

- prospective benefit is material to the customer;
- review burden does not erase saved time;
- no critical access or data-boundary incident occurs;
- the customer pays, renews, or expands; and
- integration cost supports a repeatable gross margin.

Kill or reposition the product if customers only want inventory/governance already supplied by incumbents, if no improvement remains after matched baselines, if expert review costs exceed saved work, or if every deployment requires a bespoke evaluation system.

## 17. Enterprise narrative

### Customer-facing version

“Your agents generate traces every day, but a trace is not trusted knowledge. AEON turns verified outcomes into candidate operational procedures, tests them against your incident history, routes them through your change controls, and deploys them with full lineage and rollback. Your team keeps authority; the agent improves only when the evidence passes.”

### Technical version

“AEON is a framework-neutral evidence, evaluation, and procedure-promotion layer. It normalizes agent trajectories and environment outcomes, applies deterministic authorization, evaluates candidate memories or procedures against versioned datasets and matched baselines, records accountable approval, and deploys signed artifacts with canary and rollback controls.”

### Research version

“AEON tests whether persistent, governed memory and procedure adaptation improve agent reliability across time. Claims require independent outcomes, matched baselines, ablations, repeated trials, and preserved negative evidence. No consciousness inference follows from successful task behavior.”

## 18. Recommended immediate decision

Pursue a **12-week evidence and vertical-slice programme** before building a broad platform.

The single target result should be:

> On a hidden set of historical IT incidents, an AEON-governed procedure improves end-to-end resolution performance over a static runbook and matched RAG agent, with zero unauthorized executions, complete evidence lineage, human approval, and successful rollback.

If that result cannot be demonstrated, more autonomy, longer runtimes, more models, a larger simulator, or consciousness-oriented architecture will not solve the enterprise case. If it can be demonstrated and an enterprise pays to repeat it prospectively, AEON has the beginning of a focused company.

## Research method and sources

This assessment combined:

- direct inspection of the current repository and its 39-test suite;
- review of the AEON master project, operational context, preregistration, experiment findings, hazard results, and independent scientific review;
- source inspection of runtime, policy, gateway, ledger, and improvement-lifecycle code;
- primary vendor documentation for AWS, Microsoft, NVIDIA, ServiceNow, LangSmith, Anthropic, and NIST;
- primary research papers on production agents, agent reliability, feedback memory, embodied skill acquisition, and tool-agent evaluation.

Material external sources:

1. [Measuring Agents in Production](https://arxiv.org/abs/2512.04123) — production practices and reliability challenges.
2. [tau-bench](https://arxiv.org/abs/2406.12045) — repeated-trial tool-agent reliability.
3. [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) — simple architectures, ground truth, controls, and tool design.
4. [Anthropic: Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) — outcome, trace, grader, and regression evaluation design.
5. [Anthropic: Agentic misalignment](https://www.anthropic.com/research/agentic-misalignment) — simulated risk evidence and recommended oversight boundaries.
6. [NIST AI 600-1](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence) — cross-sector generative-AI risk profile.
7. [AWS AgentCore episodic memory](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/episodic-memory-strategy.html) — managed episodic extraction, consolidation, reflection, and retrieval.
8. [AWS AgentCore Evaluations](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/evaluations.html) — framework-integrated built-in and custom evaluation.
9. [Microsoft Foundry observability](https://learn.microsoft.com/en-us/azure/foundry/concepts/observability) — agent traces, pre-production evaluation, monitoring, and continuous evaluation.
10. [NVIDIA NeMo Agent Toolkit evaluation](https://docs.nvidia.com/nemo/agent-toolkit/latest/workflows/evaluate.html) — configurable workflow evaluation and plugin evaluators.
11. [ServiceNow AI Control Tower](https://www.servicenow.com/products/ai-control-tower.html) — enterprise AI inventory, action security, governance, and value measurement.
12. [LangSmith Evaluation](https://www.langchain.com/langsmith/evaluation) — offline/online evaluation, trajectory analysis, human calibration, and CI.
13. [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) — agentic threat categories.
14. [Reflexion](https://arxiv.org/abs/2303.11366) — episodic linguistic feedback without weight updates.
15. [Voyager](https://arxiv.org/abs/2305.16291) — skill libraries, environmental feedback, and transfer in Minecraft.

Vendor capability descriptions are vendor claims, not independent evidence of customer outcomes. Commercial demand, willingness to pay, integration cost, and AEON’s incremental advantage remain validation questions.
