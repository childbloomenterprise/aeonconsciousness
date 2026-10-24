# AEON at Devin Hacks Kochi: pitch kit

**Track 2: Make the Invisible Visible.** The invisible thing is AEON's own
body and the hidden faults in it. The interesting part is what happens after
detection: AEON weighs explanations, runs a diagnostic experiment, revises
itself, and reuses the revision without failing again.

## Before judges arrive (2 minutes)

1. Windows: double-click `run_demo.bat`. macOS/Linux: `./run_demo.sh`. This runs the 10 tests, then serves `http://127.0.0.1:8770`.
2. Check the page loads and the tick counter moves. No internet or API keys needed.
3. Have `docs/aeon_develop_dashboard.png`, `artifacts/aeon-develop-ablation/REPORT.md` and the recorded demo video open in tabs as backups.

## The 2-minute pitch (click **▶ Guided demo** as you start talking)

> **0:00 — Hook.** "Most AI is told what its body is. AEON isn't. It starts with
> unlabeled sensors and motors, and has to discover what belongs to it."
>
> **0:15 — Development (screen: body map filling in).** "It babbles, notices
> that two signals track its own commands (its body), tests which signal is an
> object by trying to touch it, and measures its own reach."
>
> **0:35 — Secret sabotage (scene 2).** "Now I secretly add a 3-tick delay to its
> motors. It misses. Instead of retrying blindly, it considers four
> explanations: the world changed, my eyes are wrong, my action failed, my
> timing changed. Then it picks the experiment that best separates them: one tiny
> test movement. The hand moved 3 ticks late, so it revises its self-model:
> delay 0→3."
>
> **1:00 — Transfer (scene 3).** "A ball is thrown. It predicts that reacting
> would miss with its lag, so it spends a thought on imagining the throw. It
> catches it first try. No new failure needed."
>
> **1:15 — Vision + tool (scenes 4–6).** "Bias its vision: it feels for the
> object and recalibrates its eyes. Attach an unknown tool: a new signal
> appears, it works out the signal is part of its body and that its reach grew."
>
> **1:35 — The science.** "Is this one self-model doing the work, or just
> memory and compute? We pre-registered 16 predictions with a hash, then ran 20
> seeds. Freeze the self-model and delay recovery falls from 0.94 to 0.21, but
> memory loss doesn't touch it. Cut the self-model from attention and only the
> vision faults break. 15 of 16 predictions held, and we report the one that
> didn't."
>
> **1:55 — Close.** "AEON is an inspectable, testable mechanism for a
> perspective that develops through action. We don't claim it's conscious. We
> show that its self-model plays a causal role."

## Likely judge questions

| Question | Answer |
|---|---|
| What did you build today? | `aeon_develop/` is new: world, self-model, inquiry, metacognition, situation graph, plasticity, ablation experiment, dashboard, 10 tests. The older AEON packages in the repo are untouched (see the PR diff). |
| Is it just hard-coded? | Sensor and motor labels are shuffled per seed, and body discovery is regression plus active experiments. The diagnostic likelihood tables are hand-specified on purpose so every inference is inspectable. That is a stated limit. |
| Why not use an LLM? | An LLM is one of its options ("consult LLM"), at a cost. It's a generic stub here, and AEON learns to trust it less (`advisor.trust` falls) because it can't see AEON's body. Its relations drive decisions before any words are generated. |
| How do you know the self-model matters? | Pre-registered ablations. Each one breaks a different set of abilities: frozen breaks delay, catch, vision and tool; attention cut breaks only vision; memory loss breaks none of the self-model abilities; a simple adaptive controller can't anticipate or extend itself. |
| What failed? | P11: we predicted memory loss would slow re-diagnosis of a recurring delay. It didn't (29 vs 28 ticks), because the first experiment is already optimal. We report it. |
| Is it conscious? | No claim. The numbers are internal estimates. It's a candidate mechanism whose causal role can be tested; showing experience would need more evidence. |
| What's next? | Learn the likelihood tables from experience, put a real LLM behind the advisor and measure when it helps, and move to the repo's AI2-THOR 3-D backend. |
| What was the hardest bug? | Development once paired the light sensor with an object coordinate by coincidence. The fix was scientific: AEON now replicates a touch before believing a signal is an object. |

## If something breaks

* **Dashboard stalls:** click **▶ Guided demo** again (it restarts a fresh life), or set speed to *fast*.
* **Laptop or Python problem:** play the recorded video and walk through `REPORT.md`.
* **Asked to run the experiment live:** `python -m aeon_develop experiment --seeds 5` takes about 5 seconds.
