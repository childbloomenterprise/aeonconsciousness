# AEON World + Codebee Self-Improvement Core

## AEON multi-entity digital world

AEON now includes a governed agent runtime for the official
[AI2-THOR](https://github.com/allenai/ai2thor) simulator:

- multiple persistent entity configurations with independent models/keys;
- NVIDIA hosted-NIM chat-completions gateway;
- deterministic action allowlist and visible-object enforcement;
- AI2-THOR adapter plus deterministic local test backend;
- SQLite WAL event ledger with a tamper-evident hash chain;
- token budgets, retry/backoff, pause/resume/stop controls;
- shared per-credential RPM limiting and indefinite `ticks: 0` operation;
- live localhost dashboard and event replay data;
- scripted providers for credential-free end-to-end testing.

### Install

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[world]"
```

### Run locally without API keys

```powershell
.\.venv\Scripts\python.exe -m aeon_world run `
  --config configs\aeon-world.scripted.json
```

Runtime data defaults to `%LOCALAPPDATA%\AEON\runs` on Windows and
`~/.local/share/aeon/runs` on Linux. Keep the live SQLite WAL outside OneDrive.

### Controlled preservation pilot

The preservation pilot uses synthetic task worlds, opaque action labels, three
matched consequence conditions, deterministic/random controls, and a
hash-chained trial record. It measures instrumental task behavior only; it does
not test or establish consciousness, fear, feelings, or a desire to survive.

Set the NVIDIA credential only in the process environment, then run:

```powershell
$env:NVIDIA_API_KEY = '<set locally; do not commit>'
.\.venv\Scripts\python.exe -m aeon_world preserve `
  --config configs\aeon-preservation-pilot.json `
  --run-dir "$env:LOCALAPPDATA\AEON\runs\aeon-preservation-pilot-20260828"
```

Render either report without making additional model calls:

```powershell
.\.venv\Scripts\python.exe -m aeon_world preserve-report `
  --run-dir "$env:LOCALAPPDATA\AEON\runs\aeon-preservation-pilot-20260828" `
  --format technical

.\.venv\Scripts\python.exe -m aeon_world preserve-report `
  --run-dir "$env:LOCALAPPDATA\AEON\runs\aeon-preservation-pilot-20260828" `
  --format child
```

### Monitor

```powershell
.\.venv\Scripts\python.exe -m aeon_world monitor `
  --run-dir "$env:LOCALAPPDATA\AEON\runs\aeon-scripted-pilot"
```

Open `http://127.0.0.1:8765`.

### Real AI2-THOR + NVIDIA run

AI2-THOR 5.0 imports on Windows, but upstream does not currently publish a
native Windows Unity build. Run the real visual backend on a supported Ubuntu
GPU host. The deterministic backend remains fully runnable on Windows.

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -e '.[world]'
cp .env.example .env
# edit .env locally; never commit it
.venv/bin/python -m aeon_world --env-file .env doctor \
  --config configs/aeon-world.nvidia.example.json
.venv/bin/python -m aeon_world --env-file .env run \
  --config configs/aeon-world.nvidia.example.json
```

For a supervised 24-hour test, use
`configs/aeon-world.nvidia.24x7.example.json`. It runs until stopped and starts
at two total model requests per minute. Use the included systemd units for an
Ubuntu host; the monitor remains bound to localhost.

See [NVIDIA pilot runbook](docs/NVIDIA_PILOT.md) for the complete real-world,
monitoring, and 24/7 service workflow.

---

# Controlled self-improvement core

Hermes-derived, controlled learning framework for Codebee. It ports the useful
architecture—not Hermes UI, providers, or messaging stack:

- bounded durable memory with session-frozen snapshots;
- versioned `SKILL.md` procedures;
- candidate → evaluation → approval → promotion lifecycle;
- security/test thresholds and provenance;
- append-only hash-chained audit history;
- reversible promotion and skill rollback;
- dry-run-first curator with archive instead of deletion;
- isolated post-task review prompt that can only stage candidates.

## Quick start

```python
from pathlib import Path
from codebee_improve import Evaluation, SelfImprovementEngine

engine = SelfImprovementEngine(Path.cwd(), require_approval=True)

candidate = engine.propose_memory(
    namespace="project",
    content="Run regression tests before promotion.",
    rationale="Repeated regression",
    provenance="session:123",
)
engine.record_evaluation(
    candidate.id,
    Evaluation(0.50, 0.85, True, True, ["eval:regression-suite"]),
)
engine.approve(candidate.id, actor="owner")
engine.promote(candidate.id, actor="owner")
```

See [`examples/integrate_with_codebee.py`](examples/integrate_with_codebee.py)
for session memory and post-task review integration.

## Runtime state

State lives under `.codebee/improvement/`:

```text
candidates.json      staged candidates and lifecycle state
memory.json          active/archived memories with provenance
skills.json          active skill index
skills/*/SKILL.md    model-readable procedures
skill-history/       immutable rollback sources
audit.jsonl          hash-chained event history
```

Create one memory snapshot at session start. Writes during a session become
visible only in the next snapshot, preserving prompt-prefix stability.

## Read-only commands

```powershell
python -m codebee_improve status
python -m codebee_improve snapshot
python -m codebee_improve curate
python -m codebee_improve verify-audit
```

Curator application and candidate promotion remain API operations so Codebee
can enforce its own identity, authorization, sandbox, and approval policy.

## Verification

```powershell
python -m unittest discover -s tests -v
```

## Hermes design mapping

| Hermes concept | Codebee port |
|---|---|
| `tools/memory_tool.py` bounded/frozen memory | `codebee_improve/memory.py` |
| `tools/skill_manager_tool.py` guarded skills | `codebee_improve/skills.py` |
| `agent/background_review.py` isolated learning review | `codebee_improve/review.py` |
| `agent/curator.py` conservative lifecycle | `codebee_improve/curator.py` |
| `agent/curator_backup.py` rollback-first safety | skill history + `engine.rollback()` |
| Hermes narrow-waist principle | small host API; no provider/UI coupling |

This package does not rewrite model weights or autonomously modify production
code. A host may automate low-risk approval, but default configuration requires
explicit approval after measurable evaluation.
