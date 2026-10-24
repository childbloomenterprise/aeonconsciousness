"""Competing interpretations of a surprise, and experiments that tell them apart."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from .situation import SituationGraph

WORLD = "world_changed"
VISION = "vision_unreliable"
FAILED = "action_failed"
TIMING = "action_timing_changed"
HYPOTHESES = (WORLD, VISION, FAILED, TIMING)

DESCRIPTIONS = {
    WORLD: "The world changed (the object really moved).",
    VISION: "My visual sensor is unreliable (biased or noisy).",
    FAILED: "My action failed (motor commands are not executing).",
    TIMING: "My action's timing changed (commands land late or early).",
}

# P(outcome | hypothesis) for each experiment. Hand-specified and inspectable.
EXPERIMENTS: dict[str, dict[str, dict[str, float]]] = {
    "re_observe": {
        WORLD: {"stable": 0.92, "jitter": 0.08},
        VISION: {"stable": 0.5, "jitter": 0.5},
        FAILED: {"stable": 0.92, "jitter": 0.08},
        TIMING: {"stable": 0.92, "jitter": 0.08},
    },
    "probe_pulse": {
        WORLD: {"as_expected": 0.9, "lag_changed": 0.05, "none": 0.05},
        VISION: {"as_expected": 0.9, "lag_changed": 0.05, "none": 0.05},
        FAILED: {"as_expected": 0.05, "lag_changed": 0.05, "none": 0.9},
        TIMING: {"as_expected": 0.06, "lag_changed": 0.9, "none": 0.04},
    },
    "touch_probe": {
        WORLD: {"at_seen": 0.85, "offset": 0.1, "none": 0.05},
        VISION: {"at_seen": 0.25, "offset": 0.65, "none": 0.1},
        FAILED: {"at_seen": 0.05, "offset": 0.05, "none": 0.9},
        TIMING: {"at_seen": 0.5, "offset": 0.3, "none": 0.2},
    },
}
EXPERIMENT_COST = {"re_observe": 4, "probe_pulse": 12, "touch_probe": 35}
EXPERIMENT_PURPOSE = {
    "re_observe": "hold still and look again: does the reading jitter?",
    "probe_pulse": "one small diagnostic movement: when (if ever) does my hand respond?",
    "touch_probe": "go feel for the object where I see it: is it really there?",
}


def _normalize(p: dict[str, float]) -> dict[str, float]:
    s = sum(p.values()) or 1.0
    return {k: v / s for k, v in p.items()}


def entropy(p: dict[str, float]) -> float:
    return -sum(v * math.log2(v) for v in p.values() if v > 1e-12)


def expected_info_gain(posterior: dict[str, float], experiment: str) -> float:
    table = EXPERIMENTS[experiment]
    outcomes = next(iter(table.values())).keys()
    h0 = entropy(posterior)
    gain = 0.0
    for o in outcomes:
        po = sum(posterior[h] * table[h][o] for h in posterior)
        if po <= 0:
            continue
        post = _normalize({h: posterior[h] * table[h][o] for h in posterior})
        gain += po * (h0 - entropy(post))
    return gain


def priors_from_graph(graph: SituationGraph, symptoms: dict[str, float]) -> tuple[dict[str, float], list[str]]:
    """Priors are read from the connected representation of the present."""
    p = {h: 1.0 for h in HYPOTHESES}
    reasons: list[str] = []
    if symptoms.get("motion_error", 0) > 0.35:
        p[FAILED] *= 2.5
        p[TIMING] *= 2.5
        reasons.append("my hand did not move as predicted → suspect my own action")
    if symptoms.get("vision_jump", 0) > 0.5:
        p[WORLD] *= 2.0
        p[VISION] *= 2.0
        reasons.append("the object's seen position jumped without my doing")
    if symptoms.get("inconsistency", 0) > 0.3:
        p[VISION] *= 3.0
        reasons.append("touch and vision disagree")
    target = graph.intended_object()
    if target and graph.has_edge("self", "moved", target) and graph.has_edge(f"prediction:{target}", "contradicted_by"):
        p[WORLD] *= 1.5
        p[VISION] *= 1.5
        reasons.append(f"{target} is the one I moved and its position contradicts my prediction")
    for edge in graph.edges_from(target or "", "uncertain_because"):
        p[VISION] *= 1.8
        reasons.append(f"I am uncertain because {edge['dst']} was unreliable earlier")
    if symptoms.get("grip_failed", 0) > 0.5 and symptoms.get("motion_error", 0) <= 0.35 and symptoms.get("vision_jump", 0) <= 0.5:
        p[VISION] *= 1.5
        p[WORLD] *= 1.3
        reasons.append("grip failed although my movement looked normal")
    return _normalize(p), reasons


@dataclass
class InquiryStep:
    kind: str
    detail: str
    posterior: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "detail": self.detail, "posterior": {k: round(v, 3) for k, v in self.posterior.items()}}


@dataclass
class Inquiry:
    started: int
    trigger: str
    symptoms: dict[str, float]
    posterior: dict[str, float]
    reasons: list[str] = field(default_factory=list)
    steps: list[InquiryStep] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    conclusion: str | None = None
    revision: str | None = None
    ended: int | None = None
    advisor_label: str | None = None
    recalled: str | None = None

    def log(self, kind: str, detail: str) -> None:
        self.steps.append(InquiryStep(kind, detail, dict(self.posterior)))

    def apply_evidence(self, likelihood: dict[str, float], kind: str, detail: str) -> None:
        self.posterior = _normalize({h: self.posterior[h] * max(1e-4, likelihood.get(h, 1e-4)) for h in self.posterior})
        self.log(kind, detail)

    def update(self, experiment: str, outcome: str, detail: str) -> None:
        table = EXPERIMENTS[experiment]
        self.apply_evidence({h: table[h][outcome] for h in self.posterior}, experiment, f"{outcome}: {detail}")

    def choose_experiment(self, counts: dict[str, int]) -> tuple[str, dict[str, float]]:
        scores = {}
        for e in EXPERIMENTS:
            if counts.get(e, 0) >= 2:
                continue
            scores[e] = expected_info_gain(self.posterior, e) - 0.004 * EXPERIMENT_COST[e]
        best = max(scores, key=scores.get)
        return best, scores

    def best(self) -> tuple[str, float]:
        h = max(self.posterior, key=self.posterior.get)
        return h, self.posterior[h]

    def to_dict(self) -> dict[str, Any]:
        return {
            "started": self.started,
            "ended": self.ended,
            "trigger": self.trigger,
            "symptoms": {k: round(v, 2) for k, v in self.symptoms.items()},
            "reasons": self.reasons,
            "posterior": {k: round(v, 3) for k, v in self.posterior.items()},
            "steps": [s.to_dict() for s in self.steps],
            "conclusion": self.conclusion,
            "revision": self.revision,
            "advisor_label": self.advisor_label,
            "recalled": self.recalled,
        }
