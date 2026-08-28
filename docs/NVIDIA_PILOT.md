# AEON × AI2-THOR × NVIDIA pilot runbook

## Honest capability boundary

This repository now provides a complete AEON orchestration vertical slice. It
does not vendor AI2-THOR's Unity source or scene binaries. The official
`ai2thor==5.0.0` package downloads the Unity build on first controller launch.

Current upstream host support:

- Ubuntu/macOS: official runtime path;
- Windows: Python package imports, but public native Unity build currently
  unavailable;
- WSL2: possible on some systems but not treated as validated production path;
- recommended 24/7 host: Ubuntu GPU workstation or GPU VM.

## Architecture

```text
AI2-THOR Unity world
        ↓ observations + RGB frames + metadata
AEON entity contexts
        ↓
NVIDIA model gateway
        ↓ structured JSON proposal
Deterministic action policy
        ↓ allowed AI2-THOR command
AI2-THOR state transition
        ↓
Hash-chained SQLite ledger + JPEG frames + live monitor
```

Models cannot call Unity directly. They receive only bounded observations and
visible object identifiers. The policy rejects unknown actions, extra
parameters, invisible object targets, forced interactions, teleportation, and
invalid movement magnitudes.

## 1. Ubuntu host preparation

Install Python 3.11+, NVIDIA drivers, Vulkan utilities, and an X server if not
using AI2-THOR CloudRendering. Allow roughly 800 MB for the current first Unity
build download (the tested AI2-THOR 5.0 archive reported 769 MB).

```bash
git clone <your-aeon-repository-url> aeon
cd aeon
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[world]'
```

## 2. Credentials

```bash
cp .env.example .env
chmod 600 .env
```

Set local secrets:

```text
NVIDIA_API_KEY=...
```

Entity identity, model ID, and credential alias remain separate. Do not rotate
credentials to bypass provider limits. Keys never enter prompts, events, world
state, or dashboard responses. One key can serve multiple entity/model
configurations. Requests sharing that key also share a process-wide 30 RPM
limiter; retry attempts count against that cap.

### Windows workstation through WSL2

The project and deterministic backend were validated under Ubuntu 26.04/WSL2
with NVIDIA GPU passthrough. AI2-THOR's Unity archive download starts correctly,
but WSL rendering remains an upstream-unofficial path. From an Ubuntu terminal:

```bash
sudo apt-get update
sudo apt-get install -y python3-venv
python3 -m venv ~/.venvs/aeon
~/.venvs/aeon/bin/python -m pip install -e '/mnt/c/Users/vaish/OneDrive/Documents/ChatGPT/AEON 1[world]'
cd '/mnt/c/Users/vaish/OneDrive/Documents/ChatGPT/AEON 1'
~/.venvs/aeon/bin/python -m aeon_world --env-file .env run \
  --config configs/aeon-world.nvidia.example.json
```

First real launch downloads the current 769 MB Linux Unity build. Do not stop
the process during that one-time download when bandwidth permits.

## 3. Doctor

```bash
.venv/bin/python -m aeon_world --env-file .env doctor \
  --config configs/aeon-world.nvidia.example.json
```

Required:

- `ai2thor_import: true`;
- `native_ai2thor_runtime: true`;
- every configured credential `present: true`;
- `nvidia-smi` and `vulkaninfo` successful when CloudRendering is enabled.

## 4. Credential-free vertical slice

```bash
.venv/bin/python -m aeon_world run \
  --config configs/aeon-world.scripted.json \
  --run-dir "$HOME/.local/share/aeon/runs/aeon-scripted-pilot"
```

Verify:

```bash
.venv/bin/python -m aeon_world verify \
  --run-dir "$HOME/.local/share/aeon/runs/aeon-scripted-pilot"
```

## 5. Real AI2-THOR/NVIDIA run

Terminal 1:

```bash
.venv/bin/python -m aeon_world --env-file .env run \
  --config configs/aeon-world.nvidia.example.json
```

Terminal 2:

```bash
.venv/bin/python -m aeon_world monitor \
  --run-dir "$HOME/.local/share/aeon/runs/aeon-nvidia-pilot" \
  --host 127.0.0.1 --port 8765
```

Remote access through SSH tunnel:

```bash
ssh -L 8765:127.0.0.1:8765 user@aeon-host
```

Then open `http://127.0.0.1:8765` locally.

## 6. 24/7 services

The 24/7 example uses `ticks: 0` (run until stopped), two entities, one model
decision per entity each 60 seconds, and an explicit per-entity token budget.
That cadence produces 2 RPM total before retries. Tune only after observing
latency, 429 responses, token usage, and trial-credit consumption.

Copy and edit example units:

```bash
sudo cp deployment/aeon-world.service.example /etc/systemd/system/aeon-world.service
sudo cp deployment/aeon-monitor.service.example /etc/systemd/system/aeon-monitor.service
sudo systemctl daemon-reload
sudo systemctl enable --now aeon-world aeon-monitor
```

Inspect:

```bash
systemctl status aeon-world aeon-monitor
journalctl -u aeon-world -f
```

Dashboard controls write a local control file read by the runner:

- Resume;
- Pause at tick boundary;
- Stop gracefully.

Stopping through the dashboard exits successfully, so `Restart=on-failure`
does not relaunch an intentionally stopped experiment. Crashes restart after
10 seconds.

## 7. Evidence exported for NVIDIA

Each run directory contains:

```text
events.sqlite3       run state and complete hash-chained event stream
events.sqlite3-wal   active write-ahead log while running
frames/<entity>.jpg  latest first-person view for each entity
control.json         external pause/resume/stop command
```

Event types:

```text
world_started
observation
decision
action_denied
action_result
model_error
budget_exhausted
heartbeat
world_error
world_stopped
```

Use `aeon-world verify` before reporting results. Keep raw run directory as
experiment evidence.

## 8. Pilot completion gate

- two NVIDIA model configurations complete 100 ticks;
- every action preceded by observation and decision events;
- invalid/invisible-object actions denied;
- token budgets enforced;
- provider failures produce `Done`, not uncontrolled actions;
- dashboard remains responsive;
- event hash chain verifies;
- no credential values appear in database or logs;
- AI2-THOR frames and metadata correspond to acting entity.

## 9. Credential-free Kilo fallback

`configs/aeon-world.kilo.8h.json` uses two explicitly free Kilo Gateway
models through its anonymous OpenAI-compatible endpoint. It runs for eight
hours at one tick per 75 seconds: approximately 96 requests/hour, below Kilo's
documented 200 free requests/hour/IP limit. Free routes may log prompts and
outputs; send simulated world state only, never personal or confidential data.

The included WSL user services run the experiment and localhost monitor:

```bash
mkdir -p ~/.config/systemd/user
cp deployment/aeon-kilo-8h.user.service ~/.config/systemd/user/
cp deployment/aeon-kilo-monitor.user.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now aeon-kilo-monitor.service
systemctl --user enable --now aeon-kilo-8h.service
```

Inspect without changing experiment state:

```bash
python -m aeon_world report --run-dir ~/.local/share/aeon/runs/aeon-kilo-8h
```
