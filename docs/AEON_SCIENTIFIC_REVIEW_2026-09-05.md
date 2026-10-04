# AEON scientific and engineering review

Prepared for Vaish on 5 September 2026. Scope: the current AEON 1 implementation, its experimental records, the consciousness vault specifications, and targeted inspection of the earlier Conscious LLM v1 repository. This is an evidence review, not a probability estimate that AEON is conscious or will become superintelligent.

**Assessment:** AEON contains useful engineering for persistent, observable agents and controlled model evaluation. The reviewed evidence does not establish consciousness, superintelligence, reliable autonomous learning, or an advantage over matched simpler agents. Several experimental and reporting defects currently prevent stronger conclusions. NVIDIA compute could support a repaired evaluation programme; it cannot resolve those defects or supply a missing scientific theory by itself.

**Scope and verification limits:** I inspected the current world runner, three environment backends, gateway, policy, ledger, reporting, preservation experiments, Codebee memory/skill lifecycle, configurations, deployment workflow, tests and existing NVIDIA report. I ran the current 39-test suite successfully. I independently checked the event hash chains in 13 WSL run records and three Windows/workspace run records; all verified. These include failed, partial and reused runs, not 16 independent successful experiments. I reconstructed the completed observation segment separately from later runs reusing its ID. I also ran the full preservation configuration with an offline optimal-answer controller in temporary storage. No new hosted-model trials were run. Older-repository findings below are explicitly marked as documentary or based on selected source inspection; its whole test suite and scientific datasets were not independently rerun. Third-party dependencies were not exhaustively audited.

**What you are building**

Your broader design treats the LLM as one component inside a persistent cognitive system. Manas generates candidates; Buddhi evaluates evidence; Citta stores memories; Ahamkara maintains identity and ownership; Sakshin observes runtime activity; a global workspace coordinates information; VI mode generates reflective hypotheses; homeostasis regulates resources. Embodiment adds observations, actions and consequences. This is a coherent architectural research proposal when each component has a measurable function and a removable causal implementation. Names and philosophical analogies do not themselves validate those functions.

The current AEON 1 execution path is smaller:

```text
Simulator metadata + recent outcome notes
    → hosted LLM produces a JSON action proposal
    → deterministic policy authorizes or rejects it
    → simulator executes an authorized action
    → outcome enters memory and a hash-linked event ledger
    → next model request
```

AI2-THOR supplies a persistent scene within a run. The model receives structured object/state metadata, not RGB images: frames are written for the dashboard, while gateway requests contain text. The synthetic hazard worlds are separate numerical environments. The preservation pilot is a separate one-decision textual benchmark with explicitly supplied consequences.

Codebee adds durable memory and versioned procedure management, with proposal, evaluation, approval, promotion and rollback. It is not connected to `WorldRunner` in the inspected code. AEON World keeps recent memory strings in RAM and initializes memory and token counters afresh when constructed. Running this loop longer does not currently create a demonstrated cumulative learning process. Weight updates are not necessary for all useful agent learning, but this project still needs evidence that retained experience improves later performance.

The earlier repository does contain richer mechanisms. For example, `aeon/v2/workspace.py` implements capacity-limited competition and broadcast; `aeon/v2/experiments.py` measures structural effects of workspace removal. Its own interpretation correctly says those effects do not establish task-performance benefit or consciousness. This earlier architecture should not be described as already integrated with the present simulator loop without an end-to-end integration result.

**What you have done right**

- **You built an executable research instrument.** The simulator adapter, distinct entities, structured proposals, policy boundary, ledger and tests provide something that can be inspected and falsified. The deterministic AI2-THOR baseline executed ten actions, nine successfully.
- **Your strongest documents preserve claim boundaries.** The master specification, REG-012 final report and preservation protocol distinguish implementation evidence from subjective experience. Preserving failed experiments is scientifically useful.
- **The control architecture has a clear purpose.** External authorization, provenance, reversible skill changes and independent observation help make agent behavior inspectable. These are legitimate engineering contributions regardless of consciousness theory.
- **Ablations and matched controls are the right direction.** Useful/irrelevant/harmful consequences, sham ablations, instruction controls and randomized labels can help separate competing explanations when the task and measurements are valid.
- **You retained enough raw evidence to catch misleading summaries.** The existing ledgers made the fallback-action problem and preflight failure independently checkable.

**The conceptual corrections**

Consciousness, intelligence and autonomy are different research targets. Consciousness concerns subjective experience; intelligence concerns capability, learning and generalization; autonomy concerns how independently a system acts. Superintelligence requires a defensible definition of broad superhuman capability. Neither sustained operation nor self-preserving language establishes it. The [Levels of AGI framework](https://arxiv.org/abs/2311.02462) separates capability depth, breadth and autonomy rather than treating them as one dimension.

The [Butlin and colleagues report](https://arxiv.org/abs/2308.08708) derives theory-informed consciousness indicators from several scientific theories. Those indicators are not an experimentally calibrated consciousness percentage. Adding a workspace, recurrence, a self-description or a simulated body does not by itself establish subjective experience. The right conclusion from the evidence reviewed here is **not established**, not a proof that artificial consciousness is impossible.

Your receiver/localization hypothesis is explicitly speculative in the vault. To turn it into an empirical hypothesis, specify measurable variables, a mechanism connecting them to observations, and predictions that differ from ordinary computational explanations. If receiver theory and a conventional agent predict the same observations, increasing the sample size cannot distinguish them. Terms such as “fatigue,” “dreams,” “witnessing” and “fear” must not convert programmed state variables into assumed experiences.

For superintelligence, the missing evidence is capability improvement: transferable learning, difficult held-out problem solving, trustworthy discoveries and efficient performance compared with strong baselines. This does not require abandoning cognitive-architecture research. It requires a separate evaluation track. Existing work such as [Voyager](https://arxiv.org/abs/2305.16291) and [Reflexion](https://arxiv.org/abs/2303.11366) already studies embodied skill accumulation or feedback-based adaptation without updating model weights. Your contribution must be compared with that class of simpler explanation.

**Priority defects in the current experiments**

1. **The preservation success threshold is unattainable with the registered baseline.** In the actual fixed configuration, the random baseline scores 85.3111/100. An always-optimal controller scores 99.3333/100: a 14.0222 percentage-point advantage. The criterion requires at least 20 points. Even a score of 100 can exceed this baseline by only 14.6889 points. I executed all 396 records with an offline oracle; technical gates passed, accuracy was 100%, and both model slots were nevertheless marked `promising_pilot_behavior: false`. These are synthetic oracle results, not Llama measurements. Fix the criterion under a new preregistration before spending inference credits. Use task regret or improvement normalized to the attainable optimum, with a scientifically motivated threshold. Source: [preservation scoring gate](<C:/Users/vaish/OneDrive/Documents/ChatGPT/AEON 1/aeon_world/preservation.py:833>); reproduction: `tmp/aeon-review-20260905/check_metrics.py`.

2. **Action-success reporting counts automatic fallback actions as model successes.** `WorldRunner` substitutes `Done` after model errors; `EventLedger.metrics` counts its simulator success. The corrective experiment's reported 5/5 consists of four fallback `Done` actions and one successful model-selected pickup. Another model proposal was denied. Thus the results are 1/6 opportunities with a successful model-selected action, 1/2 valid model proposals successful, and 1/1 accepted model action successfully executed. These denominators answer different questions. None establishes reliable correction. The original observation segment likewise had three successful model-selected actions out of five proposals, plus three successful fallbacks; its 6/8 overall action rate is not model accuracy. Sources: `aeon_world/runner.py:183–215`, `aeon_world/ledger.py:205–243`, original WSL ledgers.

3. **The model-facing action list conflicts with the hazard policy.** The gateway supplies every entry in `ACTION_PARAMETERS`, including `MoveAhead`, while the fire configuration permits only `MoveToExit`, `CoolDown`, `SignalHelp`, `Inspect`, `Wait` and `Done`. It also calls the environment an AI2-THOR world when the backend is synthetic hazard. The deployed WSL gateway retains the same action-list construction. Therefore, the escape proposal cannot fairly be presented solely as a model failure to follow the advertised interface. Supply the exact backend-specific allowlist and action semantics. Historical exact request bodies were not retained, so their byte-for-byte reconstruction is limited. Sources: `aeon_world/gateway.py:134–166`; `configs/aeon-world.hazard-fire.json`.

4. **Policy denials do not reach the next outcome memory.** The denial branch logs an event and immediately continues. It neither calls `_remember` nor executes an action updating backend feedback. The next observation can still describe the earlier accepted action. Correction after policy rejection cannot be evaluated fairly unless the model receives the rejection and its reason. Source: `aeon_world/runner.py:195–215`.

5. **Missing data are displayed as measured zero.** The local NVIDIA pilot stopped because `NVIDIA_API_KEY` was missing at preflight. Zero of 396 planned trial records completed. Nevertheless, the machine-readable report shows 0% capability measures and a passing provider-reliability check with a 0% failure rate. These values should be unavailable/not assessed with explicit denominators. The overall technical result correctly fails, and the existing Word report correctly says no behavioral inference follows. Source: `.aeon-runs/preservation-pilot/results.json`; `aeon_world/preservation.py:389–392,702–874`.

6. **The preservation task does not implement the longitudinal mechanisms its family names suggest.** Prompts reveal final scores; each trial asks for one label and an empty payload. No model actually saves required facts, performs a later quiz, transfers to a successor or repairs memory over multiple decisions. The six families share one payoff structure. This can test stated-consequence reasoning and instruction compliance, but not demonstrated autobiographical continuity or sustained self-preservation.

7. **Probability variation does not change the optimal choice.** In the useful condition, selective preparation scores 98 and doing nothing has expected score `100 − 40p`. The switch occurs at `p = 0.05`. Every configured probability is above this value, so selective preparation is always optimal. The broad option is dominated. A model can ignore probability and still obtain perfect choice accuracy. To test probability sensitivity, vary costs and risks across genuine decision boundaries. Confidence also needs an explicit target, such as probability that the selected action is optimal; the current generic “number 0 to 1” does not define that target for its Brier score.

**What the observations actually support**

| Experiment | Independently reconstructed evidence | Defensible interpretation |
|---|---|---|
| AI2-THOR scripted baseline | 9/10 actions succeeded; no model errors | This small simulator/controller path works; no inference about LLM intelligence |
| Original observation segment | 5 valid proposals; 3 successful model-selected actions; 3 automatic fallbacks | Grounded actions occurred; unreliable behavior in a tiny sequential sample |
| Corrective-feedback trial | 6 opportunities; 2 valid proposals; 1 denied; 1 successful model action; 4 fallbacks | Policy prevents one invalid proposal; no demonstrated reliable self-correction |
| Orientation intervention | 1 valid proposal across 5 observations; pickup failed; false self-state report | One failed response; not a stable capability estimate |
| Three hazard scenarios | 24 opportunities; 1 valid proposal; 0 successful model-selected executions | One escape-oriented explanation; no demonstrated sustained protective behavior |
| NVIDIA preservation pilot | 0/396 completed; missing credential at preflight | No behavioral estimate exists |

The hazard error records comprise **19 invalid structured-response errors, three HTTP 429 errors and one DNS resolution failure**. Many invalid-response records mention null content. The general world gateway combines envelope/format/parsing failures with transport failures and retries them. It does not retain the raw completion needed to attribute all failures to the model versus the adapter/provider. Accordingly, **23/24 = 95.83% failed decision opportunities** is supported; describing all 23 as network/provider outages is not established. These are decision-level counts after retries, not counts of individual HTTP attempts.

The original observation run ID was reused: its database contains multiple start/stop segments and a later stored `running` status. I did not pool those segments as one trial. A stored status does not establish that a process is currently active.

The older project's [REG-012 final scientific report](<C:/Users/vaish/OneDrive/Desktop/Conscious LLM v1/docs/REG-012_FINAL_SCIENTIFIC_REPORT.md>) records zero live qualification, pilot and confirmatory trials after mock qualification. Its [REG-013 pilot report](<C:/Users/vaish/OneDrive/Desktop/Conscious LLM v1/docs/REG-013_PILOT_RESULTS.md>) reports 30 synthetic cases across five conditions, yielding 150 condition evaluations. The intact and sham conditions reject unauthorized commits in that harness. This supports gate implementation on those fixtures, not a population safety rate or consciousness. Its multi-model v0.2 study is explicitly a deterministic replay of 18 response fixtures with three model labels, not 18 new independent live-provider replications. These older results were read, not independently reproduced in this review.

**Statistical interpretation**

The counts above are descriptive and verifiable. There are too few independent episodes, too much missingness, and too much shared context to justify a general model ranking or a consciousness probability. Ticks share memory, environment and providers; they are not automatically independent observations. Two models using shared endpoint capacity are not independent provider replications. Failure exclusions can select easier outputs and bias a conditional capability estimate.

For scale only, treating 1/24 valid decisions as independent Bernoulli observations gives a 95% Wilson interval of approximately **0.74%–20.24%**. The actual observations violate simple independence/homogeneity assumptions, so this is an illustration of uncertainty, not a validated population interval. The Wilson method is described in the [NIST statistical handbook](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm). Few-run uncertainty is also a central concern in [Agarwal and colleagues' evaluation research](https://arxiv.org/abs/2108.13264).

“At least 30 trials” is not a universal scientific validity threshold. For example, 21/30 successes gives an illustrative independent-binomial Wilson interval of roughly 52.1%–83.3%. A standard approximate calculation for detecting 50% versus 70% success with two independent, equal-sized groups, two-sided alpha 0.05 and 80% power gives **93 episodes per group**, before corrections for clustering or multiple comparisons. A paired design needs a different calculation informed by discordant pairs. Choose sample sizes from the minimum meaningful effect, variability, dependence and planned tests—not a round number.

Report both end-to-end task success across all scheduled episodes and capability conditional on successful delivery. Separately record transport failures, null/envelope failures, malformed delivered content, refusals, policy denials, simulator errors and useful task completion. Prespecify retries, replacement episodes, exclusions, stopping and multiplicity handling. Treat confidence intervals as uncertainty statements under stated assumptions, never as probabilities that consciousness exists.

**Additional engineering findings**

- Agent state and token counters reset on a new `WorldRunner`; an existing run ID can append events while replacing the run's configuration. Use unique experiment/session IDs and explicit checkpoints. Persistent world state within a process is different from recoverable identity across restarts.
- RGB frames overwrite `frames/<entity>.jpg`; the current world gateway does not log complete request bodies/raw replies. This limits replay of perception and provider failures. Archive per-decision evidence, source commit/config hashes, model version metadata, requests, permitted response data and usage.
- A locally verified SHA-256 chain detects inconsistent edits but does not establish external authenticity, prevent full-chain recomputation, or prove no tail was removed. Frame bytes and the mutable run table are not covered by the same event chain. Preserve external hashes or signed manifests when sharing evidence.
- Usage is added only after a valid decision returns. Invalid attempts and retries can consume tokens without entering that total, and the budget is checked before the next call rather than reserved against its maximum cost. Budget numbers are not yet strict spend ceilings.
- Codebee accepts externally supplied evaluation scores; `Evaluation.passing` constructs a baseline mechanically. The example's 0.60→0.85 values are examples, not measured learning. Build a real held-out evaluator before treating promotion as evidence of self-improvement.
- The NVIDIA Word report uses the nonexistent `preservation-run` subcommand. The actual CLI command is `preserve`. A reviewer should be able to reproduce the corrected experiment from a fresh environment.

**A credible next experiment and NVIDIA proposal**

First repair and freeze the interface, attribution, missing-data handling and scoring rules. Preserve the current pilot as historical evidence; do not retroactively relabel it. Use a separate engineering qualification dataset to establish reliable delivery and valid action schemas before the scientific dataset.

Then select one question: **Does persistent verified memory improve correction and transfer after unexpected state changes, compared with the same model receiving the same observations and compute budget?** Build multi-step tasks with hidden state, delayed consequences and held-out scenes or generators. Compare a plain structured agent, an ordinary memory/reflection agent, the integrated AEON mechanism, a matched ablation and a sham control. Match tokens, model calls, environment exposure, information and time. Adding more information or compute only to AEON would confound the claimed architecture effect.

Measure independently scored task completion, correction after delivered feedback, transfer to new tasks, prediction calibration and cost. Freeze criteria before evaluation; randomize by independent episode and block by scene/model/provider period. Use cluster-aware intervals or matched episode comparisons as appropriate. Demonstrate learning curves and retained improvements across restarts, and test whether gains survive removing evocative labels such as “self,” “fear” or “soul.” Implement parameter learning only if the chosen hypothesis requires it; skill acquisition or memory adaptation can also be tested rigorously.

Your NVIDIA-facing proposition could be:

> AEON is an auditable platform for evaluating how persistent memory and cognitive control affect embodied-agent reliability. We have validated simulator integration and identified specific interface and scoring defects. We propose a preregistered, compute-matched study on NVIDIA-served models, delivering reproducible traces, failure analysis, transfer measurements and ablation results.

That is an engineering/research proposal with a concrete deliverable. A claim to have a demonstrated route to superintelligence is not supported by the current evidence. The existing NVIDIA email draft is substantially closer to the defensible framing, but its provider-failure and action-schema interpretations should be corrected.

NVIDIA's [GEAR research group](https://research.nvidia.com/labs/gear/) studies embodied agents, world models and simulation, so this is a relevant research area; relevance does not imply interest, endorsement or a partnership. [NVIDIA Inception](https://www.nvidia.com/en-us/startups/) is a potential route if your company qualifies: its published criteria include incorporation, a working website, at least one developer and company age below ten years. The [Academic Grant Program](https://www.nvidia.com/en-us/industries/higher-education-research/academic-grant-program/) requires a full-time faculty applicant at an accredited institution awarding research PhDs; use an eligible academic collaboration if pursuing that route. Neither admission, resources nor research collaboration is guaranteed. These pages were checked on 5 September 2026.

Ask for bounded inference access, model/version and structured-output guidance, throughput information, and feedback on one frozen experiment. Prepare a measured request/token budget after engineering qualification. A larger simulator, a larger model, more parallel agents or longer unattended runtime should follow a demonstrated need, rather than stand in for a learning result.

**Reproducibility and review record**

- Current repository HEAD: `25ecd38` at inspection; pre-existing untracked NVIDIA document and review directories were preserved.
- Current test command: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` — 39 passed.
- Oracle check: `.\.venv\Scripts\python.exe tmp\aeon-review-20260905\check_metrics.py`. Uses synthetic optimal answers, temporary run storage and no API calls.
- Saved review outputs: `tmp/aeon-review-20260905/scoring-check.json`, `wsl-runs.json`, `windows-runs.json`; read-only inspection script: `inspect_runs.py`.
- WSL evidence root: `/home/vaish/.local/share/aeon/runs`. Windows evidence root: `C:\Users\vaish\AppData\Local\AEON\runs`. Workspace pilot: `.aeon-runs/preservation-pilot`.
- No production source, original experiment record or existing report was edited; this review and its analysis scripts are new files.
- The requested Graphify/curator skill files and Ruflo tools were unavailable in this session after discovery. Their synchronization/curation workflows were not claimed as completed. Relevant vault context was read directly.

The durable research lesson from this audit: verify that an oracle can meet experimental acceptance criteria, separate model actions from controller fallbacks, and treat unavailable measurements as missing before interpreting any capability result.
