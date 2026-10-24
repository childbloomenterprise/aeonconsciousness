"""A simpler adaptive controller: same body discovery, no revisable self-model."""

from __future__ import annotations

from typing import Any

from .agent import Aeon, Gen, Task, _dist


class SimpleAdaptiveController(Aeon):
    """Reactive controller that only adapts a speed gain from success/failure."""

    name = "simple-adaptive-controller"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.gain = 1.0

    def steer(self, target, speed=0.45):  # type: ignore[override]
        return super().steer(target, speed * self.gain)

    def life(self) -> Gen:
        yield from self.develop()
        self.sm.freeze()
        while True:
            self.new_channels.clear()
            task = self.session.next_task() if self.session else None
            if task is None:
                self.phase, self.current_task = "idle", None
                yield from self.hold(1)
                continue
            yield from self.run_task(task)

    def think(self, task: Task) -> Gen:
        task.thought = "act"
        return
        yield

    def handle_trigger(self) -> Gen:
        self.trigger = None
        return False
        yield

    def run_far(self, task: Task) -> Gen:
        yield from self.hold(2)
        yield from self.run_fetch(task, budget=45)

    def run_catch(self, task: Task, budget: int = 45) -> Gen:
        yield from self.hold(3)
        task_failures0 = self.grip_failures
        t0, await_until = self.n, -1
        while self.n - t0 < budget:
            a, landing = self.steer(self.obj_est)
            grip = self.n > await_until and _dist(landing, self.obj_est) < 0.35
            if grip:
                await_until = 10**9
            yield from self._act(a, grip=grip)
            if self.holding:
                task.success = True
                return
            if await_until == 10**9 and task_failures0 < self.grip_failures:
                break
        task.success = False

    def reach(self) -> float:
        return 0.5

    def after_task(self, task: Task, utility: float) -> None:
        old = self.gain
        self.gain = min(1.0, self.gain * 1.15) if task.success else max(0.15, self.gain * 0.7) if task.misses else self.gain
        if abs(old - self.gain) > 1e-3:
            self.trace.record("controller.gain", old, self.gain, "success-adaptive-gain", f"task success={task.success}")
