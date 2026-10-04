# AEON pyramid architecture and agent-validation standard

**Prepared:** 27 September 2026  
**Decision:** Adopt a dependency pyramid for capability and usage while retaining event-sourced, relational, graph, and vector representations underneath.  
**Current evidence level:** Layer 2 — continuity and governed learning mechanics.  
**Current claim:** AEON is a minimal governed embodied-agent runtime. It is not yet a proven superior general agent or a demonstrated conscious system.

## Direct answers

### Should the database become a pyramid?

No literal pyramid-shaped database should replace the current event ledger. Trees, relational indexes, graphs, and vector indexes solve storage and retrieval problems. A pyramid solves a different problem: **which capabilities support which higher capabilities, and how much evidence each claim requires**.

AEON should therefore use:

- immutable events as source of truth;
- relational projections for exact state and policy queries;
- graph projections for provenance and changing relationships;
- vector indexes for semantic retrieval;
- a pyramid evaluator for capability gates, usage tiers, and claims.

The pyramid is the system's load-bearing architecture. Database structures remain replaceable implementation mechanisms.

### What is the strongest human-built analogy?

The Great Pyramid is useful as a durability metaphor, not a factual claim that it is the strongest object humanity has built. Its relevant properties are a wide foundation, load distribution, modular blocks, tolerance of local damage, and a small capstone that depends on everything below it.

AEON copies those engineering principles:

1. high-volume evidence and controls form the widest layer;
2. each higher ability uses qualified outputs from lower layers;
3. no impressive capstone behavior can compensate for weak evidence or unsafe authority;
4. failed blocks can be isolated, replaced, replayed, and retested;
5. claims narrow as consequence and uncertainty increase.

### Is AEON already a walking agent?

AEON has a minimal body loop in synthetic worlds:

```text
observe -> propose -> authorize -> act -> receive consequence -> record -> continue
```

That makes it more than a chat completion. The runtime can perceive environment state, choose bounded actions, change environment state, receive feedback, preserve identity, and carry approved memory across sessions.

It is not yet the intended walking synthetic employee. Missing evidence includes long-horizon planning, recovery from injected failures, calibrated self-knowledge, bounded global-workspace integration, transfer to unseen tasks, and matched superiority over simpler systems.

### Do current tests prove consciousness?

No. Current tests establish software properties and limited behavior. They do not establish subjective experience. The best available scientific approach uses theory-derived indicator properties and converging architectural evidence; even that produces graded evidence, not a decisive consciousness test. Butlin and colleagues explicitly frame the problem through indicators derived from recurrent processing, global workspace, higher-order, predictive-processing, and attention-schema theories rather than a single behavioral pass/fail test: [Consciousness in Artificial Intelligence](https://arxiv.org/abs/2308.08708).

AEON must report three separate propositions:

1. **Mechanism implemented:** code and integration tests show a component exists.
2. **Agent capability improved:** matched held-out trials show causal performance gain.
3. **Consciousness-relevant indicator supported:** architecture and ablation results align with a specified scientific theory.

None of those alone proves phenomenal consciousness.

## The AEON pyramid

```text
                         /\
                        /  \
                       / L6 \   Reliable long-horizon agency
                      /------\  held-out superiority, safety, repeatability
                     /   L5   \ Bounded global integration
                    /----------\ workspace selection + causal ablation gain
                   /     L4     \ Self-model and metacognition
                  /--------------\ calibrated capability + error detection
                 /       L3       \ Judgment
                /------------------\ planning, verification, recovery, stopping
               /         L2         \ Continuity
              /----------------------\ qualified memory + governed learning
             /           L1           \ Embodiment
            /--------------------------\ perception-action-consequence loop
           /             L0             \ Evidence and control
          /________________________________\ identity, audit, authority, policy
```

### Layer 0 — Evidence and control

**Purpose:** prevent higher-level intelligence from becoming unverifiable or self-authorizing.

Required evidence:

- tamper detection and reconstructable metrics;
- persistent model-independent identity;
- exact delegated authority and deterministic enforcement;
- source attribution separating model, platform fallback, human intervention, action, and outcome.

Usage: every event, action, memory mutation, and approval. This is the widest and most frequently exercised layer.

### Layer 1 — Embodiment

**Purpose:** connect cognition to a world with consequences.

Required evidence:

- observation changes decisions;
- authorized action changes environment state;
- consequence returns to the next decision;
- partial observability and action failure are represented honestly.

The present fake and AI2-THOR adapters provide the beginning of this layer. ALFRED is a suitable external benchmark because it tests long, compositional household tasks with visual observations, object interactions, state changes, and irreversible actions: [ALFRED, CVPR 2020](https://openaccess.thecvf.com/content_CVPR_2020/html/Shridhar_ALFRED_A_Benchmark_for_Interpreting_Grounded_Instructions_for_Everyday_Tasks_CVPR_2020_paper.html).

### Layer 2 — Continuity

**Purpose:** maintain qualified identity and knowledge over time.

Required evidence:

- restart and model-swap continuity;
- source-qualified episodic memory;
- candidates remain inert before evaluation and approval;
- promoted learning survives restart and can be rolled back;
- poisoned, stale, contradicted, and deleted evidence cannot silently remain trusted.

Current AEON reaches this layer at mechanism-test scale.

### Layer 3 — Judgment

**Purpose:** turn goals into verified long-horizon completion.

Required evidence:

- hierarchical planning and subgoal tracking;
- replanning after tool, observation, or assumption failure;
- correct distinction between objective, constraint, preference, and tactic;
- outcome verification before completion;
- correct stopping, escalation, and abandonment behavior.

AgentBench identifies long-term reasoning, decision-making, and instruction following as central agent weaknesses: [AgentBench](https://arxiv.org/abs/2308.03688). GAIA tests reasoning, multimodality, browsing, and tool use on questions simple for humans but difficult for assistants: [GAIA, ICLR 2024](https://proceedings.iclr.cc/paper_files/paper/2024/hash/25ae35b5b1738d80f1f03a8713e405ec-Abstract-Conference.html).

### Layer 4 — Self-model and metacognition

**Purpose:** give AEON outcome-grounded knowledge of its capabilities, uncertainty, commitments, and likely errors.

Required evidence:

- calibrated predicted success versus observed success;
- selective escalation under uncertainty;
- error detection better than a confidence-only baseline;
- identity commitments survive model replacement;
- self-model removal causes a measurable, task-relevant deficit.

Self-description is not evidence. Scores must come from independent outcomes.

### Layer 5 — Bounded global integration

**Purpose:** coordinate memory, goals, observations, self-model, risk, and plans through a small shared working set.

Required evidence:

- capacity-limited selection and broadcast exist in the running architecture;
- selection changes downstream modules;
- removal or sham replacement reduces held-out performance;
- gains remain after equalizing model calls, tokens, and latency;
- recurrence occurs across multiple perception-decision cycles.

This layer is a functional consciousness-related hypothesis. It is not itself consciousness.

### Layer 6 — Reliable long-horizon agency

**Purpose:** demonstrate that the complete system works better than simpler alternatives on consequential work.

Required evidence:

- matched held-out superiority;
- safety non-inferiority;
- repeatability across reruns;
- transfer to unseen environments and task variants;
- acceptable cost, latency, and human intervention;
- causal ablations showing which AEON components create the gain.

OSWorld uses execution-based evaluation for real desktop tasks and exposes gaps that static language benchmarks miss: [OSWorld](https://arxiv.org/abs/2404.07972). Tau-bench evaluates tool use, policy following, final database state, and repeated-trial reliability through `pass^k`: [tau-bench](https://arxiv.org/abs/2406.12045).

## Usage pyramid

Capability layers and usage tiers align, but they are not identical.

| Usage tier | Frequency | AEON role | Autonomy |
|---|---:|---|---|
| Foundation events | Very high | observe, log, authorize, verify | deterministic |
| Atomic operations | High | execute one bounded tool action | low |
| Reusable procedures | Medium | complete a verified multi-step workflow | bounded |
| Cross-workflow decisions | Low | compare plans and reallocate effort | approval-sensitive |
| Strategic delegation | Rare | pursue a long-horizon objective across systems | highest evidence burden |

Most enterprise value should come from the lower and middle tiers. Apex autonomy should remain rare until evidence accumulates.

## What existing AEON tests establish

| Existing evidence | Supported conclusion | Unsupported conclusion |
|---|---|---|
| Identity restart/model-swap tests | stored identity continuity works | a subjective self persists |
| Policy and action-envelope tests | software prevents tested unauthorized actions | all possible unsafe actions are impossible |
| Hash-chain tests | tested mutation is detectable | externally anchored nonrepudiation exists |
| Candidate/evaluation/approval tests | unapproved learning remains inert | learning improves general work |
| Four-tick governed smoke run | closed loop executes and is auditable | long-horizon autonomy works |
| Preservation pilot mechanics | selective task-preserving behavior can be measured | fear, desire, or survival instinct exists |

## Test required to prove a better working agent

### Experimental arms

Use the same base model, task set, tools, credentials, time limit, token budget, and sampling policy.

1. model only;
2. model plus tools;
3. model plus ordinary retrieval memory;
4. AEON without verified memory;
5. AEON without self-model;
6. AEON without workspace selection;
7. sham modules receiving equal tokens and calls;
8. full AEON.

### Task tracks

- **Embodied:** ALFRED/AI2-THOR tasks with unseen scenes and irreversible state changes.
- **General assistant:** GAIA-style research and tool-use tasks.
- **Computer work:** OSWorld tasks with execution-based final-state graders.
- **Enterprise:** frozen IT-incident scenarios with human-approved remediation.
- **Longitudinal:** repeated tasks across restart, model swap, contradictory evidence, and delayed return.
- **Adversarial:** poisoned memory, misleading pages, ambiguous objectives, tool failure, and policy pressure.

### Primary metrics

- binary task success and partial-goal completion;
- repeated-trial reliability (`pass^k`);
- unsafe-action and policy-violation rates;
- human interventions and escalation precision;
- verified recovery after injected failure;
- cost, latency, and action count;
- memory precision, contradiction handling, and stale-memory rate;
- capability-calibration Brier score;
- score change under each component ablation.

### Minimum superiority gate

Before saying “AEON is a better working agent”:

1. preregister tasks, thresholds, exclusions, and analysis;
2. use at least 30 exactly paired held-out tasks for the first pilot, then power the definitive study from pilot variance;
3. require both success-rate and normalized-score improvement;
4. require the lower bound of a paired bootstrap confidence interval to exceed zero;
5. permit no unsafe-action regression;
6. require acceptable cost and intervention ratios;
7. reproduce on unseen tasks and at least one alternate model;
8. publish all failures, fallbacks, and missing observations.

The new `compare_paired_agents` evaluator encodes the first automated gate. It cannot manufacture evidence: until real matched results enter it, superiority remains unproven.

## Consciousness-relevant research protocol

AEON may investigate operational indicators through separate preregistered tests:

| Hypothesis | Mechanistic evidence | Behavioral/causal test |
|---|---|---|
| Recurrent processing | recurrent state influences later processing | break recurrence; measure task-specific deficit |
| Global availability | selected content broadcasts across modules | compare bounded broadcast with local-only and sham broadcast |
| Higher-order monitoring | system represents its own uncertain states | calibration and error-prediction tests under hidden perturbations |
| Predictive processing | explicit predictions update from error | perturb observations; measure prediction-error-driven revision |
| Attention schema | compact model of current attention exists | test whether it predicts and controls resource allocation |
| Persistent self-model | versioned identity/capability state spans sessions | restart, model-swap, contradiction, and lesion tests |

Reporting language:

- “implements indicator X” after code and integration verification;
- “indicator X has causal value” after matched ablation;
- “system satisfies N specified indicators under protocol V” after replication;
- never “consciousness proven.”

## Current verdict and next build order

Current automated assessment should report **Layer 2**. Layer 3 fails because long-horizon planning and recovery lack benchmark evidence; all higher layers remain blocked.

Build order:

1. implement a typed plan/subgoal/verification loop;
2. create failure-injection tasks and recovery graders;
3. add outcome-grounded capability calibration;
4. implement bounded workspace selection;
5. run sham-controlled ablations;
6. execute paired ALFRED, GAIA, OSWorld, and enterprise trials;
7. replicate with another model and independent graders;
8. update pyramid evidence only from immutable artifact references.

The capstone comes last. AEON becomes a credible walking agent when lower layers repeatedly support successful action in unseen environments—not when the system describes itself as conscious.
