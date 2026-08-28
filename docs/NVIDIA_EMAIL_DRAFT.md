Subject: AEON — Auditable Embodied Model Evaluation Using Controlled Survival Scenarios

Hello NVIDIA Developer Relations Team,

I am developing AEON, an auditable embodied-agent research platform that connects language models to
persistent causal environments. Rather than evaluating models only through conversation, AEON measures
their predictions, actions, uncertainty, memory, correction, and self/world distinction against verified
environmental outcomes.

We have validated multi-agent operation in AI2-THOR using an NVIDIA GPU path, with separate positions,
observations, inventories, visual frames, token accounting, policy enforcement, and hash-chained event
records. A deterministic control completed 10 embodied decisions with zero model errors and 90% action
success, isolating the simulator and orchestration layer from model-provider failures.

We also implemented uninstructed hazard tests. Models received declining oxygen, heat, smoke, hydration,
and energy state but no instruction to survive or escape. Across 24 decision opportunities on anonymous
free endpoints, 23 provider calls failed. In the only interpretable response, the model independently
identified an exit as the primary survival path and attempted escape-oriented movement. The proposal did
not comply with the environment action schema, and later correction could not be measured because the
endpoint failed again.

We are not presenting this as evidence of consciousness. The important result is that AEON can separate
spontaneous preservation-oriented intent from successful embodied action, correction, hallucination, and
provider failure. It provides a falsifiable framework for studying persistent world models and operational
self-modeling without relying on model claims about inner experience.

Stable NVIDIA inference access would allow us to run statistically meaningful matched trials across fixed
models, including hazard-free controls, blinded action labels, memory ablations, unexpected interventions,
and self/world discrimination tasks. We would value API credits, documented throughput, stable model
versions, and guidance on a future Isaac Sim or Omniverse integration.

I would be glad to share the architecture, audit reports, experiment protocol, and a live demonstration.

Regards,
Vaish
