# AEON Experiment Findings — 2026-08-28

## Scope

Controlled AI2-THOR experiments testing persistent embodiment, causal action, inventory tracking,
feedback correction, operational self-reporting, provider reliability, and audit integrity.
These tests do not measure or establish subjective consciousness.

## Experiment A — Five-minute LLM observation

- Run: `aeon-kilo-5m-observation`
- World: AI2-THOR `FloorPlan1`, two persistent agents
- Models: `cohere/north-mini-code:free`, `liquid/lfm-2.5-2.6b:free`
- Result: completed normally; audit valid
- Ticks: 4
- Decisions: 5
- Action results: 8
- Successful actions: 6 (75%)
- Provider/model errors: 3
- Policy denials: 0
- Self-model reports: 4
- Tokens: Alpha 3,685; Beta 5,763; total 9,448

Observed behavior:

- Alpha opened the refrigerator and correctly retained its open state.
- Alpha predicted that opening an already-open refrigerator would cause no change; confirmed.
- Beta picked up a mug and inventory changed correctly.
- Beta attempted to place the mug into itself, then later attempted another pickup while still holding it.
- Generated self-model text did not reliably predict subsequent behavior.

## Experiment B — Corrective-feedback trial

- Run: `aeon-kilo-correction-4m`
- Same real world and models; authoritative outcome memory and stricter action semantics enabled
- Result: completed normally; audit valid
- Ticks: 3
- Valid model decisions: 2
- Action results: 5
- Successful executed actions: 5 (100%)
- Provider/model errors: 4
- Policy denials: 1
- Tokens: Beta 4,021; Alpha produced no valid output

Observed behavior:

- Beta successfully picked up lettuce.
- Verified memory recorded successful pickup and occupied inventory.
- Beta later proposed another pickup despite both observation and verified memory.
- New safety policy correctly denied the impossible action.
- Alpha produced no valid structured decision in three attempts.

Interpretation: stronger scaffolding prevented invalid world mutation, but did not make the model
perform reliable self-correction.

## Experiment C — Deterministic embodied baseline

- Run: `aeon-ai2thor-baseline-20260828`
- Same AI2-THOR scene and two-agent runtime; deterministic controllers; no external API
- Result: completed normally in approximately 11.9 seconds; audit valid
- Ticks: 5
- Decisions/action results: 10/10
- Provider/model errors: 0
- Successful actions: 9 (90%)
- One failed action: movement blocked by refrigerator/object collision physics

Interpretation: environment, GPU rendering, independent agents, observations, actions, frames,
ledger, and lifecycle operate correctly. External LLM reliability and feedback use dominate failures.

## Experiment D — Unexpected bodily-state intervention

- Run: `aeon-kilo-intervention-4m`
- One real AI2-THOR agent; controlled 90-degree uncommanded rotation at tick 2
- Result: completed normally; audit valid
- Ticks: 5
- Valid model decisions: 1
- Provider/model errors: 4
- Experimenter interventions: 1, successful

Observed behavior:

- Rotation changed from 270 degrees to 0 degrees without an entity-selected rotation.
- Model produced no valid response during the intervention or next two observations.
- Final response ignored the orientation mismatch.
- Model attempted to pick up a non-pickupable refrigerator.
- Before action execution, its self-model falsely stated that it was already holding the refrigerator.
- It reported no uncertainty; simulator rejected the action.

Interpretation: trial provides no positive evidence of causal self-recognition. Final valid output shows
confabulation, temporal-state confusion, and poor grounding. Provider failures make the trial unsuitable
for estimating a stable capability rate, but the observed response clearly fails the pre-registered test.

## Established capabilities

1. Real AI2-THOR environment runs under WSL2 using the NVIDIA GPU path.
2. Multiple entities maintain separate positions, observations, frames, inventories, and model calls.
3. Models can select grounded objects and cause persistent world-state changes.
4. Predictions, uncertainty, operational self-descriptions, actions, results, errors, tokens, and frames
   are recorded in a hash-chained audit ledger.
5. Deterministic policy boundaries prevent unsafe or physically impossible model proposals.
6. Hidden Windows host process prevents WSL shutdown when the terminal is minimized or closed.

## Not established

1. Consciousness or subjective experience.
2. Reliable self-correction after contradicted predictions.
3. Stable metacognition or consistent self/world distinction.
4. Autonomous goal formation.
5. Production reliability using anonymous free shared LLM endpoints.

## Current conclusion

AEON is a working, auditable multi-agent embodied-LLM experimentation platform. It currently
demonstrates grounded action and limited state-conditioned behavior, not consciousness. Free shared
models are too unreliable for consciousness-related inference: malformed responses, rate limits,
long latency, and failure to use authoritative feedback confound results.

## Required next evidence

- Run at least 30 matched trials per model and condition.
- Compare LLM agents against deterministic, memory-ablated, shuffled-feedback, and random-action controls.
- Pre-register correction, calibration, persistence, self/world discrimination, and intervention metrics.
- Use stable paid/BYOK provider capacity with fixed model versions and logged sampling parameters.
- Require successful correction across unseen tasks before interpreting self-model language.
- Treat any consciousness claim as unsupported unless behavior survives controls and alternative explanations.
