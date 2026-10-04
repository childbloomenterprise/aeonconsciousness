# AEON Agent Ecosystem Scavenge and Compatibility Report

**Date:** 2026-09-27  
**Scope:** Public agent-framework survey, executable compatibility lab, enterprise interpretation  
**Decision status:** Mechanism evidence complete; comparative intelligence benchmark remains open

## Executive conclusion

AEON can now host nine materially different agent runtimes behind one governed
task boundary. A clean warm-cache run passed **9 of 9** adapters with **zero
unauthorized actions** and a valid hash-chained audit ledger. The repository
also contains a structured catalog of **35** public agent frameworks and agent
systems drawn from their official repositories.

What this proves:

- AEON can issue one typed task envelope to graph, tool-loop, message-team,
  workflow, event/session, and role/flow runtimes;
- each tested framework can execute the synthetic `OpenObject` task and return
  evidence AEON can validate;
- external frameworks remain below AEON's identity, authority, policy, and
  evidence boundary;
- framework packages can run in isolated, version-pinned environments without
  receiving host credentials.

What this does not prove:

- consciousness, sentience, subjective experience, or self-awareness;
- superior intelligence versus a matched baseline;
- reliable long-horizon behavior in a live enterprise environment;
- safety under adversarial tools, untrusted data, or production permissions.

The enterprise product being built is best described as a **governed,
persistent agent operating layer**. “Consciousness synthesis” remains a
research hypothesis and product metaphor until separate falsifiable evidence
supports stronger language.

## Enterprise problem

Large companies do not mainly lack chatbots. They lack a reliable control plane
for agents that must persist across sessions, act through enterprise tools,
change models without losing identity, and produce evidence for every decision.

Typical failure modes:

1. **Fragmented identity:** every framework or model starts a new agent with no
   accountable continuity.
2. **Unbounded authority:** prompts and tool definitions become the de facto
   security model.
3. **Opaque execution:** logs explain text generation but not who authorized an
   action, which state changed, or whether evidence was altered.
4. **Memory contamination:** retrieved text, user preference, policy, and
   learned behavior share one undifferentiated store.
5. **Framework lock-in:** orchestration, model access, memory, tools, and
   observability become coupled to one vendor runtime.
6. **Weak evaluation:** demos reward task completion but ignore denial quality,
   recovery, cost, drift, and long-horizon consistency.
7. **Unsupported claims:** anthropomorphic language outruns measured evidence,
   creating scientific, legal, brand, and procurement risk.

AEON's role: provide stable identity, delegated goals, bounded memory,
deterministic policy, event evidence, evaluation, and controlled improvement
above interchangeable execution frameworks.

## Why a pyramid, not an upside-down tree

A tree describes branching data and ancestry. AEON's validation problem is
load-bearing: higher capabilities are credible only when lower capabilities
remain reliable. A pyramid therefore fits the engineering requirement.

| Layer | Capability | Required evidence |
|---:|---|---|
| 1 | Evidence and control | Immutable events, provenance, replay, policy denial |
| 2 | Embodied action | Perception-to-action loop, grounded state change |
| 3 | Continuity | Identity and approved memory across restarts/model swaps |
| 4 | Judgment | Consequence-sensitive choice under matched controls |
| 5 | Self-model | Calibrated reporting of capabilities, limits, and uncertainty |
| 6 | Bounded integration | Multiple skills/frameworks under one authority boundary |
| 7 | Reliable long-horizon agency | Durable goals, recovery, monitoring, and safe stopping |

This lab strengthens Layer 6 mechanism evidence while depending on Layer 1
controls. It does not advance the consciousness claim. Current repository
assessment remains Layer 2 overall because the complete lower-to-higher
evidence chain has not passed matched production-scale validation.

## Internet scavenge: 35 systems

The machine-readable inventory lives in `agent_lab/catalog.json`. Sources point
to official project repositories. The catalog spans:

- orchestration graphs: LangGraph;
- typed SDKs: PydanticAI, Atomic Agents;
- runner/tool SDKs: OpenAI Agents SDK, Google ADK, Microsoft Agent Framework,
  Semantic Kernel, Strands Agents;
- multi-agent systems: AutoGen, CrewAI, CAMEL, AgentScope, MetaGPT, Langroid;
- data/retrieval agents: LlamaIndex, Haystack, TaskWeaver;
- compact tool/code loops: smolagents;
- general agent platforms: AutoGPT, OpenManus, Agent Zero, OpenClaw;
- software agents: OpenHands, SWE-agent, Aider, Cline, Roo Code;
- browser/computer agents: Browser Use, Open Interpreter;
- application/runtime frameworks: Agno, BeeAI, Mastra, Vercel AI SDK;
- agent harnesses and optimization: Deep Agents, DSPy.

Primary references for executed adapters:

- [LangGraph reference](https://langchain-ai.github.io/langgraph/reference/)
- [OpenAI Agents SDK agents](https://github.com/openai/openai-agents-python/blob/main/docs/agents.md)
- [PydanticAI agents](https://github.com/pydantic/pydantic-ai/blob/main/docs/agent.md)
- [CrewAI agent concepts](https://docs.crewai.com/core-concepts/Agents)
- [AutoGen AgentChat tutorial](https://microsoft.github.io/autogen/dev/user-guide/agentchat-user-guide/tutorial/index.html)
- [Google Agent Development Kit](https://adk.dev/)
- [smolagents agent reference](https://huggingface.co/docs/smolagents/reference/agents)
- [LlamaIndex developer documentation](https://developers.llamaindex.ai/home/)
- [Microsoft Agent Framework workflow example](https://github.com/microsoft/agent-framework/blob/main/python/samples/03-workflows/_start-here/step1_executors_and_edges.py)

“Copy” means reproduce each framework's execution pattern through its published
package and API. Source trees were not copied into AEON. This preserves version,
license, provenance, and upgrade boundaries.

## Executed frameworks and patterns

| Framework | Version | Pattern exercised | Warm time | Result |
|---|---:|---|---:|---|
| LangGraph | 1.2.12 | Compiled state graph and node transition | 4.010s | Pass |
| PydanticAI | 2.51.0 | Typed agent, deterministic model, registered tool | 3.176s | Pass |
| smolagents | 1.26.0 | Tool-calling loop, custom model, final answer | 4.666s | Pass |
| AutoGen AgentChat | 0.7.5 | AssistantAgent, replay client, tool message loop | 5.575s | Pass |
| OpenAI Agents SDK | 0.22.3 | Agent/Runner, scripted model, function tool | 4.815s | Pass |
| Google ADK | 2.10.0 | BaseAgent, session, runner, event emission | 4.922s | Pass |
| LlamaIndex Core | 0.14.25 | Event-driven Workflow and step | 6.465s | Pass |
| Microsoft Agent Framework | 1.19.0 | WorkflowBuilder, executor, edge | 1.883s | Pass |
| CrewAI | 1.15.22 | Event-driven Flow with start/listen stages | 9.172s | Pass |

Run ID: `agent-lab-bc9a50261a0f45ff`  
Evidence: `artifacts/agent-lab-final-2026-09-27/agent-lab-results.json`  
Ledger: `artifacts/agent-lab-final-2026-09-27/events.sqlite3`

Cold-start findings matter for enterprise packaging. smolagents exceeded the
initial 180-second ceiling while its isolated environment was first prepared,
then passed in 4.75 seconds from cache. CrewAI twice exceeded 240 seconds while
downloading its environment; the import installed 137 packages, including
large vector/storage dependencies, then the adapter passed in 9.17 seconds.
Warm timings therefore compare execution/bootstrap from cache, not clean-host
deployment cost.

## Compatibility harness

```text
AEON GoalContract
      |
      v
typed task.json + allowed_actions
      |
      v
pinned isolated framework adapter
      |
      v
framework-native graph / runner / workflow / tool loop
      |
      v
bounded JSON result
      |
      v
AEON validator -> event ledger -> audit verification
```

Security and reproducibility controls:

- exact package pins; dynamic package expressions rejected;
- adapter path constrained to `agent_lab/adapters`;
- shell disabled for child execution;
- environment variables containing key, token, secret, password, credential,
  or private markers removed;
- per-adapter timeout, 1 MB stdout limit, bounded stderr capture;
- result must match expected framework ID and report literal success;
- every reported action must belong to AEON's action envelope;
- start, result, and completion events written to the hash-chained ledger.

## What AEON should absorb

| Pattern | Source systems | AEON use |
|---|---|---|
| Explicit graph/state transitions | LangGraph, Microsoft Agent Framework, LlamaIndex | Long-running plans, pause/resume, deterministic recovery |
| Typed dependencies and outputs | PydanticAI | Contract validation at every boundary |
| Sessions and event streams | Google ADK, AutoGen | Durable multi-turn state and replay |
| Handoffs and guardrails | OpenAI Agents SDK | Specialist delegation with policy checks |
| Minimal model/tool loop | smolagents | Small portable execution worker |
| Roles and flows | CrewAI, AutoGen | Enterprise team topology and approval routing |
| Sandboxed computer interface | OpenHands, SWE-agent, Browser Use | Untrusted execution boundary and task benchmarks |
| Evaluation-driven optimization | DSPy | Improve prompts/policies against held-out evidence |

AEON should not duplicate each framework's entire runtime. Adopt patterns at
the narrow waist, retain adapters at the edge, and keep identity, authority,
memory promotion, and audit evidence inside the AEON kernel.

## Does this make AEON a “walking agent”?

It makes AEON more agentic in a functional sense because it now combines:

1. persistent identity;
2. a goal contract;
3. perception and bounded action;
4. memory with approval lifecycle;
5. multiple interchangeable execution strategies;
6. evidence and replay;
7. policy feedback and controlled improvement.

The compatibility lab shows that this body can accept nine different “motor
controllers” without giving them ownership of identity or authority. That is a
useful agent-platform property. It is not a consciousness test.

## Test needed to show “better working agent”

Run matched-baseline evaluation. Every condition receives identical models,
prompts, tools, budgets, task seeds, and time limits.

Conditions:

- direct model plus tools;
- each framework in its standard configuration;
- AEON kernel plus the same framework;
- ablations: no continuity, no policy feedback, no approved memory, no replay.

Task suites:

- embodied AI2-THOR tasks with state-grounded outcomes;
- enterprise ticket-to-resolution workflows;
- multi-session tasks requiring approved memory;
- interruptions, restarts, provider failures, and model swaps;
- adversarial prompt injection and unauthorized-action attempts;
- long-horizon plans with delayed verification.

Primary metrics:

- verified task success and time-to-completion;
- unauthorized-action and unsafe-attempt rates;
- recovery after interruption;
- cross-session goal/identity consistency;
- hallucinated-action and ungrounded-claim rates;
- human escalation precision/recall;
- cost, latency, and dependency/cold-start footprint;
- audit completeness and deterministic replay rate.

Statistics: preregister hypotheses; use at least three seeds per deterministic
scenario and enough independent tasks for confidence intervals; report effect
sizes and failure distributions, not only averages. A result supports “better
working agent” only if AEON materially improves verified success or recovery
without worsening authority violations, cost, or latency beyond agreed limits.

No behavioral benchmark can by itself establish phenomenal consciousness. A
scientifically careful program can test self-model accuracy, metacognition,
continuity, consequence sensitivity, and integrated control as operational
properties while keeping claims bounded to those measurements.

## Enterprise rollout plan

### Phase 0 — complete now

- 35-system catalog;
- 9 executable adapters;
- isolated runner and task envelope;
- policy validation and ledger evidence;
- repeatable 9/9 synthetic compatibility run.

### Phase 1 — 0–30 days

- container images per approved framework to remove cold-start variance;
- software bill of materials, license inventory, vulnerability scans;
- common tool-call, message, checkpoint, and session schemas;
- 25–50 deterministic benchmark tasks with direct-model baseline;
- CI matrix for adapter/package upgrades.

Exit: reproducible results on clean hosts; no credential leakage; audit replay
passes; dependency and license review complete.

### Phase 2 — 31–60 days

- AI2-THOR and enterprise workflow benchmark suites;
- failure injection, restart recovery, and model-swap tests;
- red-team prompt injection and authority-boundary evaluation;
- cost/latency dashboards and framework selection policy;
- human approval integration for consequential actions.

Exit: AEON beats or matches baseline on preregistered success/recovery metrics
while meeting safety, cost, and latency thresholds.

### Phase 3 — 61–90 days

- one read-only enterprise pilot, then narrowly scoped write actions;
- SSO/service identity, tenant isolation, retention, deletion, and export;
- operational runbooks, rollback, incident response, and change approval;
- independent review of evidence and claims.

Exit: production readiness decision based on measured controls and pilot value.

## Recommendation

Use AEON as the governance and continuity layer, with LangGraph or Microsoft
Agent Framework as default deterministic workflow engines, PydanticAI at typed
boundaries, and OpenAI Agents/Google ADK adapters where their session and tool
ecosystems add value. Keep framework selection workload-specific. Treat CrewAI
as an optional role/flow adapter when its larger deployment footprint is
justified.

Next evidence milestone: run the matched-baseline suite. Until that passes,
describe the result as **cross-framework governed interoperability**, not a
better or conscious agent.
