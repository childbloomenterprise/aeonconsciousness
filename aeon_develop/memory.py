"""Episodic memory whose retrieval relevance is itself plastic."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .plasticity import BoundedParam, Trace

FEATURES = ("motion_error", "grip_failed", "vision_jump", "inconsistency", "moved_by_me")


@dataclass
class Episode:
    tick: int
    signature: dict[str, float]
    diagnosis: str
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"tick": self.tick, "signature": {k: round(v, 2) for k, v in self.signature.items()}, "diagnosis": self.diagnosis, "params": self.params}


@dataclass
class Placement:
    position: tuple[float, float]
    tick: int
    by: str


class Memory:
    def __init__(self, trace: Trace) -> None:
        self.trace = trace
        self.episodes: list[Episode] = []
        self.placements: dict[str, Placement] = {}
        self.relevance = {f: BoundedParam(f"memory.relevance.{f}", 0.5, 0.05, 1.0, 0.1, trace) for f in FEATURES}

    def clear(self) -> None:
        self.episodes.clear()
        self.placements.clear()

    def store(self, tick: int, signature: dict[str, float], diagnosis: str, params: dict[str, Any]) -> None:
        self.episodes.append(Episode(tick, dict(signature), diagnosis, dict(params)))
        if len(self.episodes) > 50:
            self.episodes.pop(0)

    def place(self, object_id: str, position: tuple[float, float], tick: int, by: str) -> None:
        self.placements[object_id] = Placement((round(position[0], 3), round(position[1], 3)), tick, by)

    def similarity(self, a: dict[str, float], b: dict[str, float]) -> float:
        total = sum(float(w) for w in self.relevance.values()) or 1.0
        return sum(float(self.relevance[f]) * (1 - abs(a.get(f, 0) - b.get(f, 0))) for f in FEATURES) / total

    def recall(self, signature: dict[str, float]) -> tuple[Episode | None, float]:
        best, score = None, 0.0
        for ep in reversed(self.episodes):
            s = self.similarity(signature, ep.signature)
            if s > score:
                best, score = ep, s
        return best, score

    def reinforce(self, signature: dict[str, float], diagnosis: str, tick: int) -> None:
        """Features that separated this diagnosis from other remembered ones gain relevance."""
        others = [e for e in self.episodes if e.diagnosis != diagnosis]
        same = [e for e in self.episodes if e.diagnosis == diagnosis]
        if not others or not same:
            return
        for f in FEATURES:
            mean_same = sum(e.signature.get(f, 0) for e in same) / len(same)
            mean_other = sum(e.signature.get(f, 0) for e in others) / len(others)
            target = min(1.0, 0.2 + abs(mean_same - mean_other))
            self.relevance[f].nudge(target, 0.3, "contrastive-relevance", f"diagnosis={diagnosis}")
