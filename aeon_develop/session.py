"""Drives one AEON life: a task queue plus hidden experimenter interventions."""

from __future__ import annotations

import random
from collections import deque
from typing import Any

from .agent import Aeon, AeonConfig, Task
from .world import ArmWorld


class Session:
    def __init__(self, seed: int = 0, config: AeonConfig | None = None, agent_cls: type[Aeon] = Aeon, live: bool = False) -> None:
        self.seed = seed
        self.world = ArmWorld(seed)
        cfg = config or AeonConfig(seed=seed)
        cfg.seed = seed
        self.agent = agent_cls(self.world, cfg, self)
        self.queue: deque[Task] = deque()
        self.live = live
        self.rng = random.Random(seed + 7)
        self.interventions: list[dict[str, Any]] = []
        self._life = self.agent.life()
        self._auto = 0

    def add(self, *tasks: Task) -> None:
        self.queue.extend(tasks)

    def next_task(self) -> Task | None:
        if self.queue:
            return self.queue.popleft()
        if self.live:
            self._auto += 1
            return self.auto_task(self._auto)
        return None

    def auto_task(self, k: int) -> Task:
        if k % 4 == 0:
            return self.catch_task(phase="live")
        return Task("fetch", phase="live")

    def catch_task(self, phase: str = "") -> Task:
        y = self.rng.uniform(2.5, 7.5)
        vy = self.rng.uniform(-0.06, 0.06)
        return Task("catch", object_id="ball", spawn=(9.6, y), velocity=(-0.28, vy), phase=phase)

    def far_task(self, phase: str = "") -> Task:
        return Task("far", object_id="far_cube", spawn=(7.9, self.rng.uniform(2.5, 7.5)), phase=phase)

    def step(self) -> None:
        next(self._life)

    def run_queue(self, max_ticks: int = 20000) -> None:
        """Run until every queued task is finished (or a tick limit)."""
        start = self.agent.n
        while self.agent.n - start < max_ticks:
            if not self.queue and self.agent.current_task is None and self.agent.phase in ("idle", "stuck"):
                return
            self.step()

    def intervene(self, kind: str, **kw: Any) -> None:
        w = self.world
        if kind == "delay":
            w.set_delay(int(kw.get("ticks", 3)))
        elif kind == "vision_bias":
            w.set_vision_bias(float(kw.get("dx", 1.3)), float(kw.get("dy", 0.4)))
        elif kind == "vision_noise":
            w.set_vision_noise(float(kw.get("sigma", 0.45)))
        elif kind == "motor_block":
            w.set_motor_block(bool(kw.get("on", True)))
        elif kind == "move_object":
            w.external_move()
        elif kind == "attach_tool":
            w.attach_tool()
        elif kind == "clear":
            w.clear_faults()
        elif kind == "catch":
            self.queue.appendleft(self.catch_task("live"))
        elif kind == "far":
            self.queue.appendleft(self.far_task("live"))
        else:
            raise ValueError(f"unknown intervention {kind}")
        self.interventions.append({"tick": self.agent.n, "kind": kind, **kw})
