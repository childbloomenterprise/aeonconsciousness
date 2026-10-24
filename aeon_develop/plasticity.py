"""Bounded, traceable adaptation: every internal change is a logged event."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TraceEvent:
    tick: int
    param: str
    old: Any
    new: Any
    rule: str
    cause: str

    def to_dict(self) -> dict[str, Any]:
        def r(v: Any) -> Any:
            return round(v, 4) if isinstance(v, float) else v
        return {"tick": self.tick, "param": self.param, "old": r(self.old), "new": r(self.new), "rule": self.rule, "cause": self.cause}


@dataclass
class Trace:
    events: list[TraceEvent] = field(default_factory=list)
    clock: int = 0
    limit: int = 5000

    def record(self, param: str, old: Any, new: Any, rule: str, cause: str) -> None:
        self.events.append(TraceEvent(self.clock, param, old, new, rule, cause))
        if len(self.events) > self.limit:
            del self.events[: len(self.events) - self.limit]

    def recent(self, n: int = 30) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self.events[-n:]]


class BoundedParam:
    """A scalar connection weight with hard bounds and a maximum step per update."""

    def __init__(self, name: str, value: float, lo: float, hi: float, max_step: float, trace: Trace) -> None:
        self.name, self.lo, self.hi, self.max_step, self.trace = name, lo, hi, max_step, trace
        self.value = min(max(value, lo), hi)
        self.frozen = False

    def nudge(self, target: float, rate: float, rule: str, cause: str) -> float:
        if self.frozen:
            return self.value
        step = rate * (target - self.value)
        step = max(-self.max_step, min(self.max_step, step))
        new = min(max(self.value + step, self.lo), self.hi)
        if abs(new - self.value) > 1e-3:
            self.trace.record(self.name, self.value, new, rule, cause)
        self.value = new
        return new

    def set(self, value: float, rule: str, cause: str) -> float:
        return self.nudge(value, 1.0, rule, cause)

    def __float__(self) -> float:
        return float(self.value)
