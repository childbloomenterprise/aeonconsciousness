"""Small 2-D world with an arm whose body AEON must discover.

Sensor and actuator labels are opaque and shuffled per seed, so nothing about
the body is given to the agent. Hidden faults can be introduced at any time.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any

WORKSPACE_X = (0.5, 7.0)
WORKSPACE_Y = (0.5, 9.5)
WORLD_SIZE = 10.0
HAND_SPEED = 0.5
BASE_REACH = 0.6
TOOL_REACH = 1.7


@dataclass
class HiddenFaults:
    delay: int = 0
    vision_bias: tuple[float, float] = (0.0, 0.0)
    vision_noise: float = 0.0
    motor_block: bool = False

    def describe(self) -> dict[str, Any]:
        return {
            "delay": self.delay,
            "vision_bias": list(self.vision_bias),
            "vision_noise": self.vision_noise,
            "motor_block": self.motor_block,
        }


@dataclass
class GripResult:
    success: bool
    distance: float
    object_id: str


@dataclass
class StepResult:
    tick: int
    observation: dict[str, float]
    grip: GripResult | None = None
    released: bool = False


@dataclass
class _Pending:
    due: int
    motor: tuple[float, ...]
    grip: bool
    release: bool


@dataclass
class WorldObject:
    object_id: str
    position: list[float]
    velocity: list[float] = field(default_factory=lambda: [0.0, 0.0])


class ArmWorld:
    """Ground truth. The agent only ever sees ``observation`` channels."""

    def __init__(self, seed: int = 0) -> None:
        self.rng = random.Random(seed)
        rotation = self.rng.uniform(0, 2 * math.pi)
        self.actuators = [f"m{i}" for i in range(4)]
        self._actuator_dirs = []
        for i in range(4):
            angle = rotation + i * math.pi / 2 + self.rng.uniform(-0.25, 0.25)
            gain = self.rng.uniform(0.8, 1.0)
            self._actuator_dirs.append((gain * math.cos(angle), gain * math.sin(angle)))
        logical = ["hand_x", "hand_y", "obj_x", "obj_y", "light", "touch"]
        order = list(range(len(logical)))
        self.rng.shuffle(order)
        self._channel_of = {logical[i]: f"s{order[i]}" for i in range(len(logical))}
        self.faults = HiddenFaults()
        self.tool_attached = False
        self.hand = [3.5, 5.0]
        self.held: str | None = None
        self.objects: dict[str, WorldObject] = {"cube": WorldObject("cube", [5.0, 7.0])}
        self.active = "cube"
        self.light = 5.0
        self.tick = 0
        self._pending: list[_Pending] = []

    # ----- ground truth helpers (never shown to the agent) -----
    @property
    def reach(self) -> float:
        return TOOL_REACH if self.tool_attached else BASE_REACH

    def truth_channel_map(self) -> dict[str, str]:
        mapping = dict(self._channel_of)
        if self.tool_attached:
            mapping["tool_contact"] = "s6"
        return mapping

    def actuator_vectors(self) -> list[tuple[float, float]]:
        return list(self._actuator_dirs)

    def active_object(self) -> WorldObject:
        return self.objects[self.active]

    def distance_to_active(self) -> float:
        obj = self.active_object().position
        return math.dist(self.hand, obj)

    # ----- experimenter controls -----
    def set_delay(self, ticks: int) -> None:
        self.faults.delay = max(0, int(ticks))

    def set_vision_bias(self, dx: float, dy: float) -> None:
        self.faults.vision_bias = (float(dx), float(dy))

    def set_vision_noise(self, sigma: float) -> None:
        self.faults.vision_noise = max(0.0, float(sigma))

    def set_motor_block(self, blocked: bool) -> None:
        self.faults.motor_block = bool(blocked)

    def attach_tool(self) -> None:
        self.tool_attached = True

    def detach_tool(self) -> None:
        self.tool_attached = False

    def clear_faults(self) -> None:
        self.faults = HiddenFaults()

    def external_move(self, position: tuple[float, float] | None = None) -> None:
        """Secretly relocate the active object (the world changed)."""
        obj = self.active_object()
        if self.held == obj.object_id:
            self.held = None
        if position is None:
            position = (self.rng.uniform(1.0, 6.5), self.rng.uniform(1.0, 9.0))
        obj.position = [float(position[0]), float(position[1])]
        obj.velocity = [0.0, 0.0]

    def spawn(self, object_id: str, position: tuple[float, float], velocity: tuple[float, float] = (0.0, 0.0)) -> None:
        self.objects[object_id] = WorldObject(object_id, [float(position[0]), float(position[1])], [float(velocity[0]), float(velocity[1])])
        self.active = object_id
        if self.held and self.held != object_id:
            self.held = None

    def activate(self, object_id: str) -> None:
        self.active = object_id

    # ----- dynamics -----
    def observe(self, rng: random.Random | None = None) -> dict[str, float]:
        rng = rng or self.rng
        obj = self.active_object().position
        bias = self.faults.vision_bias
        noise = self.faults.vision_noise + 0.02
        dist = math.dist(self.hand, obj)
        values = {
            "hand_x": self.hand[0] + rng.gauss(0, 0.015),
            "hand_y": self.hand[1] + rng.gauss(0, 0.015),
            "obj_x": obj[0] + bias[0] + rng.gauss(0, noise),
            "obj_y": obj[1] + bias[1] + rng.gauss(0, noise),
            "light": self.light,
            "touch": 1.0 if dist <= BASE_REACH else 0.0,
        }
        obs = {self._channel_of[k]: round(v, 4) for k, v in values.items()}
        if self.tool_attached:
            obs["s6"] = 1.0 if dist <= TOOL_REACH else 0.0
        return obs

    def step(self, motor: dict[str, float] | None = None, grip: bool = False, release: bool = False) -> StepResult:
        motor = motor or {}
        command = tuple(max(0.0, min(1.0, float(motor.get(name, 0.0)))) for name in self.actuators)
        self._pending.append(_Pending(self.tick + self.faults.delay, command, grip, release))
        self.tick += 1
        due = [p for p in self._pending if p.due < self.tick]
        self._pending = [p for p in self._pending if p.due >= self.tick]
        grip_result: GripResult | None = None
        released = False
        for p in due:
            if not self.faults.motor_block:
                dx = sum(a * v[0] for a, v in zip(p.motor, self._actuator_dirs)) * HAND_SPEED
                dy = sum(a * v[1] for a, v in zip(p.motor, self._actuator_dirs)) * HAND_SPEED
                norm = math.hypot(dx, dy)
                if norm > HAND_SPEED:
                    dx, dy = dx * HAND_SPEED / norm, dy * HAND_SPEED / norm
                self.hand[0] = min(max(self.hand[0] + dx, WORKSPACE_X[0]), WORKSPACE_X[1])
                self.hand[1] = min(max(self.hand[1] + dy, WORKSPACE_Y[0]), WORKSPACE_Y[1])
            if p.release and self.held:
                self.held = None
                released = True
            if p.grip and not self.faults.motor_block:
                dist = self.distance_to_active()
                ok = dist <= self.reach and self.held is None
                if ok:
                    self.held = self.active
                grip_result = GripResult(ok, dist, self.active)
        for obj in self.objects.values():
            if self.held == obj.object_id:
                obj.position = list(self.hand)
                obj.velocity = [0.0, 0.0]
                continue
            obj.position[0] += obj.velocity[0]
            obj.position[1] += obj.velocity[1]
            for axis in (0, 1):
                if not 0.0 <= obj.position[axis] <= WORLD_SIZE:
                    obj.velocity[axis] *= -1
                    obj.position[axis] = min(max(obj.position[axis], 0.0), WORLD_SIZE)
        self.light = min(max(self.light + self.rng.gauss(0, 0.25), 0.0), WORLD_SIZE)
        return StepResult(self.tick, self.observe(), grip_result, released)

    def snapshot(self) -> dict[str, Any]:
        return {
            "tick": self.tick,
            "hand": [round(v, 3) for v in self.hand],
            "objects": {k: {"position": [round(v, 3) for v in o.position], "velocity": o.velocity} for k, o in self.objects.items()},
            "active": self.active,
            "held": self.held,
            "tool_attached": self.tool_attached,
            "reach": self.reach,
            "workspace": {"x": WORKSPACE_X, "y": WORKSPACE_Y},
            "faults": self.faults.describe(),
        }
