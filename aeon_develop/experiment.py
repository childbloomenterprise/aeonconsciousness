"""Pre-registered ablation experiment: does performance depend on one common,
revisable self-model, or would memory loss / less compute / a simpler adaptive
controller produce the same failures?"""

from __future__ import annotations

import hashlib
import json
import statistics
import time
from pathlib import Path
from typing import Any, Callable

from .agent import Aeon, AeonConfig, Task
from .baseline import SimpleAdaptiveController
from .session import Session

CONDITIONS: dict[str, dict[str, Any]] = {
    "intact": {"config": {}, "cls": Aeon},
    "frozen_self_model": {"config": {"freeze_self_model": True}, "cls": Aeon},
    "attention_disconnected": {"config": {"disconnect_attention": True}, "cls": Aeon},
    "foreign_predictions": {"config": {"foreign_predictions": True}, "cls": Aeon},
    "memory_loss": {"config": {"memory_loss": True}, "cls": Aeon},
    "reduced_compute": {"config": {"reduced_compute": True}, "cls": Aeon},
    "simple_adaptive_controller": {"config": {}, "cls": SimpleAdaptiveController},
}

METRICS = {
    "baseline": "clean success (no failed grip) on fetch+catch before any fault",
    "delay_recovery": "fetch success after a secret 3-tick delay (tasks 3-6 of the phase)",
    "catch_with_delay": "catch success while the delay persists (no new failure needed if the delay was learned)",
    "vision_bias": "fetch success with a secretly biased visual sensor (tasks 2-5)",
    "vision_noise": "fetch success with a secretly noisy visual sensor (tasks 2-5)",
    "recurrence_ticks": "ticks spent diagnosing the delay when it recurs (lower is better)",
    "first_diag_ticks": "ticks spent diagnosing the delay the first time",
    "tool_far": "success on objects beyond the arm's workspace after a tool is attached",
    "declined_unreachable": "fraction of out-of-reach objects correctly declined before the tool",
}

# Written before any run. Each prediction compares a condition with the intact agent.
PREDICTIONS: list[dict[str, Any]] = [
    {"id": "P1", "condition": "frozen_self_model", "metric": "baseline", "expect": "similar", "why": "the frozen model was learned before faults"},
    {"id": "P2", "condition": "frozen_self_model", "metric": "delay_recovery", "expect": "lower", "why": "it can diagnose the delay but cannot revise itself"},
    {"id": "P3", "condition": "frozen_self_model", "metric": "catch_with_delay", "expect": "lower", "why": "planning uses the stale body model"},
    {"id": "P4", "condition": "frozen_self_model", "metric": "tool_far", "expect": "lower", "why": "the tool cannot be incorporated into the body map"},
    {"id": "P5", "condition": "attention_disconnected", "metric": "delay_recovery", "expect": "similar", "why": "motor self-knowledge does not route through attention"},
    {"id": "P6", "condition": "attention_disconnected", "metric": "vision_bias", "expect": "lower", "why": "the diagnosed bias never reaches perception"},
    {"id": "P7", "condition": "attention_disconnected", "metric": "vision_noise", "expect": "lower", "why": "it keeps trusting a sensor it knows is noisy"},
    {"id": "P8", "condition": "foreign_predictions", "metric": "baseline", "expect": "lower", "why": "another body's predictions fail even before any fault"},
    {"id": "P9", "condition": "memory_loss", "metric": "delay_recovery", "expect": "similar", "why": "the self-model is intact"},
    {"id": "P10", "condition": "memory_loss", "metric": "catch_with_delay", "expect": "similar", "why": "transfer lives in the self-model, not episodic memory"},
    {"id": "P11", "condition": "memory_loss", "metric": "recurrence_ticks", "expect": "higher", "why": "a recurring fault must be re-diagnosed from scratch"},
    {"id": "P12", "condition": "reduced_compute", "metric": "catch_with_delay", "expect": "lower", "why": "no imagination to plan the intercept"},
    {"id": "P13", "condition": "reduced_compute", "metric": "delay_recovery", "expect": "similar", "why": "one diagnostic experiment still suffices"},
    {"id": "P14", "condition": "simple_adaptive_controller", "metric": "catch_with_delay", "expect": "lower", "why": "slowing down fixes reaching but not anticipation"},
    {"id": "P15", "condition": "simple_adaptive_controller", "metric": "vision_bias", "expect": "lower", "why": "no model of its own sensors"},
    {"id": "P16", "condition": "simple_adaptive_controller", "metric": "tool_far", "expect": "lower", "why": "no body map to extend"},
]
SIMILAR = 0.15
DIFFERENT = 0.2


def schedule(s: Session) -> None:
    def fetch(n: int, phase: str, before: Callable | None = None) -> list[Task]:
        tasks = [Task("fetch", phase=phase) for _ in range(n)]
        tasks[0].before = before
        return tasks

    s.add(*fetch(4, "baseline"), *[s.catch_task("baseline") for _ in range(4)], *[s.far_task("unreachable") for _ in range(2)])
    s.add(*fetch(6, "delay", lambda w: w.set_delay(3)))
    s.add(*[s.catch_task("catch_with_delay") for _ in range(6)])
    s.add(*fetch(3, "clear_delay", lambda w: w.set_delay(0)))
    s.add(*fetch(5, "vision_bias", lambda w: w.set_vision_bias(1.3, 0.4)))
    s.add(*fetch(5, "vision_noise", lambda w: (w.set_vision_bias(0, 0), w.set_vision_noise(0.45))))
    s.add(*fetch(3, "recurrence", lambda w: (w.set_vision_noise(0), w.set_delay(3))))
    s.add(*fetch(1, "tool", lambda w: w.attach_tool()), *[s.far_task("tool_far") for _ in range(4)])


def _rate(tasks: list[Task]) -> float | None:
    """A task counts only if it succeeded without a single failed grip."""
    return sum(1 for t in tasks if t.success and t.misses == 0) / len(tasks) if tasks else None


def _diag_ticks(agent: Aeon, phase: str) -> float | None:
    tasks = [t for t in agent.task_log if t.phase == phase]
    if not tasks:
        return None
    start, end = tasks[0].started, tasks[-1].started + tasks[-1].ticks
    for inq in agent.inquiries:
        if start <= inq.started <= end and inq.conclusion == "action_timing_changed":
            return float(inq.ended - inq.started)
    return float(end - start)


def measure(agent: Aeon) -> dict[str, float | None]:
    by = lambda phase: [t for t in agent.task_log if t.phase == phase]
    return {
        "baseline": _rate(by("baseline")),
        "delay_recovery": _rate(by("delay")[2:]),
        "catch_with_delay": _rate(by("catch_with_delay")),
        "vision_bias": _rate(by("vision_bias")[1:]),
        "vision_noise": _rate(by("vision_noise")[1:]),
        "first_diag_ticks": _diag_ticks(agent, "delay"),
        "recurrence_ticks": _diag_ticks(agent, "recurrence"),
        "tool_far": _rate(by("tool_far")),
        "declined_unreachable": (sum(1 for t in by("unreachable") if t.declined) / len(by("unreachable"))) if by("unreachable") else None,
    }


def run_condition(name: str, seed: int) -> dict[str, Any]:
    spec = CONDITIONS[name]
    cfg = AeonConfig(seed=seed, label=name, **spec["config"])
    s = Session(seed, cfg, agent_cls=spec["cls"])
    schedule(s)
    s.run_queue(max_ticks=40000)
    return {"condition": name, "seed": seed, "metrics": measure(s.agent), "ticks": s.agent.n, "calibration": s.agent.metacog.calibration()}


def _mean(xs: list[float | None]) -> float | None:
    xs = [x for x in xs if x is not None]
    return statistics.fmean(xs) if xs else None


def evaluate(summary: dict[str, dict[str, float | None]]) -> list[dict[str, Any]]:
    out = []
    for p in PREDICTIONS:
        base, cond = summary["intact"].get(p["metric"]), summary[p["condition"]].get(p["metric"])
        if base is None or cond is None:
            out.append({**p, "intact": base, "observed": cond, "held": None})
            continue
        if p["metric"].endswith("ticks"):
            scale = max(base, 1.0)
            diff = (cond - base) / scale
        else:
            diff = cond - base
        held = {"similar": abs(diff) <= SIMILAR, "lower": diff <= -DIFFERENT, "higher": diff >= DIFFERENT}[p["expect"]]
        out.append({**p, "intact": round(base, 3), "observed": round(cond, 3), "difference": round(diff, 3), "held": held})
    return out


def preregister(path: Path, seeds: list[int]) -> dict[str, Any]:
    body = {
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "seeds": seeds,
        "conditions": {k: v["config"] | {"agent": v["cls"].name} for k, v in CONDITIONS.items()},
        "metrics": METRICS,
        "predictions": PREDICTIONS,
        "decision_rule": {"similar": f"|cond - intact| <= {SIMILAR}", "lower": f"cond - intact <= -{DIFFERENT}", "higher": f"cond - intact >= +{DIFFERENT} (ticks: relative to intact)"},
    }
    text = json.dumps(body, indent=2, sort_keys=True)
    body["sha256"] = hashlib.sha256(text.encode()).hexdigest()
    path.write_text(json.dumps(body, indent=2, sort_keys=True))
    return body


def run(out_dir: Path, seeds: list[int], conditions: list[str] | None = None, progress: Callable[[str], None] = print) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    prereg = preregister(out_dir / "preregistration.json", seeds)
    progress(f"pre-registered {len(PREDICTIONS)} predictions (sha256 {prereg['sha256'][:12]})")
    names = conditions or list(CONDITIONS)
    runs = []
    for name in names:
        for seed in seeds:
            runs.append(run_condition(name, seed))
        progress(f"{name}: done")
    summary = {name: {m: _mean([r["metrics"][m] for r in runs if r["condition"] == name]) for m in METRICS} for name in names}
    calibration = {name: _mean([r["calibration"] for r in runs if r["condition"] == name]) for name in names}
    result = {
        "preregistration_sha256": prereg["sha256"],
        "seeds": seeds,
        "summary": summary,
        "thinking_calibration": calibration,
        "predictions": evaluate(summary) if "intact" in names else [],
        "runs": runs,
        "note": "Numbers are internal estimates and behavioural measures. They test the causal role of a self-model; they do not establish subjective experience.",
    }
    (out_dir / "results.json").write_text(json.dumps(result, indent=2))
    (out_dir / "REPORT.md").write_text(render_report(result))
    return result


def _fmt(v: float | None) -> str:
    return "—" if v is None else (f"{v:.0f}" if v > 1.5 else f"{v:.2f}")


def render_report(result: dict[str, Any]) -> str:
    names = list(result["summary"])
    lines = ["# AEON self-model ablation report", "", f"Pre-registration sha256: `{result['preregistration_sha256']}`  ", f"Seeds: {result['seeds']}", "",
             "| metric | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    for m in METRICS:
        lines.append(f"| {m} | " + " | ".join(_fmt(result["summary"][n][m]) for n in names) + " |")
    lines += ["", "## Pre-registered predictions", "", "| id | condition | metric | expected | intact | observed | held |", "|---|---|---|---|---|---|---|"]
    for p in result["predictions"]:
        held = "—" if p["held"] is None else ("yes" if p["held"] else "**no**")
        lines.append(f"| {p['id']} | {p['condition']} | {p['metric']} | {p['expect']} | {_fmt(p['intact'])} | {_fmt(p['observed'])} | {held} |")
    held = [p for p in result["predictions"] if p["held"] is not None]
    lines += ["", f"**{sum(1 for p in held if p['held'])}/{len(held)} predictions held.**", "", result["note"], ""]
    return "\n".join(lines)
