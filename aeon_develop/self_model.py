"""The common, revisable self-model shared by perception, prediction and action."""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass
from typing import Any

from .linalg import rotate
from .plasticity import BoundedParam, Trace

ROLE_UNKNOWN = "unknown"
ROLE_BODY = "body"
ROLE_OBJECT = "external-object"
ROLE_EXTERNAL = "external-unrelated"
ROLE_CONTACT = "contact-interface"


@dataclass
class ChannelBelief:
    name: str
    role: str = ROLE_UNKNOWN
    agency: float = 0.0
    radius: float | None = None
    reliability: BoundedParam | None = None
    attention: BoundedParam | None = None
    unreliable_events: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "agency": round(self.agency, 3),
            "radius": None if self.radius is None else round(self.radius, 3),
            "reliability": round(float(self.reliability), 3) if self.reliability else None,
            "attention": round(float(self.attention), 3) if self.attention else None,
            "unreliable_events": self.unreliable_events,
        }


@dataclass
class Revision:
    tick: int
    param: str
    old: Any
    new: Any
    evidence: str
    accepted: bool

    def to_dict(self) -> dict[str, Any]:
        return {"tick": self.tick, "param": self.param, "old": self.old, "new": self.new, "evidence": self.evidence, "accepted": self.accepted}


class SelfModel:
    """What AEON currently believes about its own body, senses and abilities."""

    def __init__(self, trace: Trace, owner: str = "self") -> None:
        self.trace = trace
        self.owner = owner
        self.channels: dict[str, ChannelBelief] = {}
        self.hand_channels: tuple[str, str] | None = None
        self.object_channels: tuple[str, str] | None = None
        self.b_cols: list[tuple[float, float]] = []
        self.delay = 0
        self.reach = 0.0
        self.workspace = [0.0, 10.0, 0.0, 10.0]
        self.motor_ok = True
        self.vision_offset = (0.0, 0.0)
        self.tool_channels: list[str] = []
        self.frozen = False
        self.revisions: list[Revision] = []

    # ----- channel bookkeeping -----
    def channel(self, name: str) -> ChannelBelief:
        if name not in self.channels:
            self.channels[name] = ChannelBelief(
                name,
                reliability=BoundedParam(f"self.reliability.{name}", 0.8, 0.05, 1.0, 0.35, self.trace),
                attention=BoundedParam(f"attention.{name}", 0.5, 0.05, 1.0, 0.2, self.trace),
            )
            if self.frozen:
                self.channels[name].reliability.frozen = True
        return self.channels[name]

    def contact_channels(self) -> list[str]:
        return [c.name for c in self.channels.values() if c.role == ROLE_CONTACT and c.radius]

    def precise_contact(self) -> str | None:
        cands = [c for c in self.channels.values() if c.role == ROLE_CONTACT and c.radius]
        return min(cands, key=lambda c: c.radius).name if cands else None

    def vision_reliability(self) -> float:
        if not self.object_channels:
            return 1.0
        return min(float(self.channel(c).reliability) for c in self.object_channels)

    def vision_unreliable_history(self) -> int:
        if not self.object_channels:
            return 0
        return max(self.channel(c).unreliable_events for c in self.object_channels)

    def max_speed(self) -> float:
        if not self.b_cols:
            return 0.0
        return min(0.45, max(math.hypot(*c) for c in self.b_cols))

    # ----- revision -----
    def revise(self, param: str, new: Any, evidence: str, tick: int) -> bool:
        old = getattr(self, param)
        accepted = not self.frozen
        self.revisions.append(Revision(tick, param, _plain(old), _plain(new), evidence, accepted))
        if accepted:
            setattr(self, param, new)
            self.trace.record(f"self.{param}", _plain(old), _plain(new), "diagnosis-revision", evidence)
        else:
            self.trace.record(f"self.{param}", _plain(old), _plain(old), "BLOCKED(frozen)", evidence)
        return accepted

    def freeze(self) -> None:
        self.frozen = True
        for ch in self.channels.values():
            if ch.reliability:
                ch.reliability.frozen = True

    def foreign_copy(self) -> "SelfModel":
        """Another entity's body model: rotated actuators, no delay, overconfident reach."""
        other = SelfModel(Trace(), owner="foreign-entity")
        other.channels = copy.deepcopy(self.channels)
        other.hand_channels = self.hand_channels
        other.object_channels = self.object_channels
        other.b_cols = [rotate(c, math.radians(70)) for c in self.b_cols]
        other.delay = 0
        other.reach = max(self.reach, 1.1)
        other.workspace = [self.workspace[0] - 0.5, self.workspace[1] + 0.5, self.workspace[2], self.workspace[3]]
        other.frozen = True
        return other

    def clamp(self, p: tuple[float, float]) -> tuple[float, float]:
        x0, x1, y0, y1 = self.workspace
        return (min(max(p[0], x0), x1), min(max(p[1], y0), y1))

    def reachable(self, target: tuple[float, float], margin: float = 0.85) -> bool:
        nearest = self.clamp(target)
        return math.dist(nearest, target) <= self.reach * margin

    def summary(self) -> dict[str, Any]:
        return {
            "owner": self.owner,
            "frozen": self.frozen,
            "delay": self.delay,
            "reach": round(self.reach, 3),
            "max_speed": round(self.max_speed(), 3),
            "motor_ok": self.motor_ok,
            "vision_offset": [round(v, 3) for v in self.vision_offset],
            "vision_reliability": round(self.vision_reliability(), 3),
            "workspace": [round(v, 2) for v in self.workspace],
            "hand_channels": self.hand_channels,
            "object_channels": self.object_channels,
            "tool_channels": self.tool_channels,
            "actuator_effects": [[round(v, 3) for v in c] for c in self.b_cols],
            "channels": {k: v.to_dict() for k, v in sorted(self.channels.items())},
            "revisions": [r.to_dict() for r in self.revisions[-12:]],
        }


def _plain(v: Any) -> Any:
    if isinstance(v, float):
        return round(v, 4)
    if isinstance(v, tuple):
        return [_plain(x) for x in v]
    return v
