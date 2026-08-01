# AEON Research Core Alpha — Final Build Report

## Repository assessment

The repository was empty except for an untracked local secret file. No architecture, tests, or working components existed to preserve. Alpha was implemented as a clean local-first system with compatibility seams for cloud storage and hosted model providers.

## Implementation summary

Implemented:

- typed cognitive/event/memory/belief/self-model contracts;
- persistent identity and restart history;
- append-only JSONL events with SHA-256 chaining and HMAC witness signatures;
- structured Chitta memory with retrieval, provenance, confidence, and revision history;
- deterministic Manas candidate generation;
- configurable attention scoring and capacity-limited Global Workspace;
- bounded recurrent cognition with convergence/stagnation exit;
- metacognitive prediction, evidence/contradiction monitoring, and behavioural control signals;
- Buddhi epistemic classification and belief gate;
- Ahamkara provider/self and memory/action ownership distinction;
- operational self-model and probabilistic world-state records;
- quarantined VI Mode hypotheses;
- read-only-style Sakshin telemetry comparison and model behaviour traces;
- immutable seeded experiment definitions, ablations, and intervention specifications;
- external runtime pause, resume, snapshot, restore-review, and shutdown controls;
- deterministic MOCK, Anthropic Claude, Google Gemini, and OpenAI-compatible adapters;
- local storage plus selectable Supabase event mirror;
- FastAPI API, SSE stream, OpenAPI schema, and CORS-local development configuration;
- responsive React research console covering all twelve required research surfaces;
- Supabase RLS-enabled migration;
- architecture, cognitive, observer, metacognition, experiment, API, security, risk, decision, evaluation, and runbook documentation.

## Runtime instructions

See `docs/AEON_RUNBOOK.md` and repository `README.md`.

- MOCK: no keys; default and deterministic.
- Claude: `AEON_MODEL_PROVIDER=anthropic` plus model and API key.
- Gemini: `AEON_MODEL_PROVIDER=gemini` plus model and Google API key.
- OpenAI-compatible: provider, base URL, API key, and model.
- Local: `AEON_RUNTIME_MODE=local`.
- Supabase mirror: apply migration, configure backend URL/service key, choose `hybrid` or `cloud`.

## Test report

- Automated tests: 16 passed, 0 failed, 0 skipped.
- Python lint: passed.
- TypeScript compilation and Vite production build: passed.
- Live MOCK API cycle: passed.
- Browser: desktop and 375px viewport passed; no console errors.
- Secret scan: passed; local secret file ignored.

## Known limitations

- Hosted providers expose no private hidden thoughts or activations.
- Claude/Gemini live paid calls were not executed during final verification.
- Supabase migration was generated but not applied to the remote project; remote DDL requires an authenticated migration channel.
- Sakshin uses a logically read-only observer boundary but shares the Alpha process; process-level isolation remains future work.
- Flat-file locks are process-local. Multi-worker deployment should use PostgreSQL advisory/transactional locking.
- Experiment records are immutable and reproducible definitions; large-scale trial scheduling and statistical analysis remain a later research layer.
- Restore is manual-review-only to avoid silently replacing valid evidence history.
- Alpha is a research system, not production-ready infrastructure.
- Self-report is not ground truth; provider and architecture effects remain alternative explanations.

## Scientific status

| Property | Status |
|---|---|
| Persistent identity | TESTED |
| Structured memory | TESTED |
| Recurrent processing | TESTED |
| Global workspace | TESTED |
| Self-model | IMPLEMENTED |
| Metacognitive monitoring | TESTED |
| Metacognitive control | TESTED |
| Observer independence | PARTIALLY_IMPLEMENTED |
| Self-report fidelity | TESTED |
| Intervention detection | NOT_TESTED |
| Consciousness relevance | AMBIGUOUS |
| Phenomenal consciousness | UNKNOWN |

Architectural and behavioural indicators do not establish phenomenal consciousness.
