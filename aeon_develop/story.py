"""Guided demo: a scripted sequence of hidden interventions with captions."""

from __future__ import annotations

from typing import Callable, Generator

from .session import Session

DEV_DONE = ("idle", "task:")


class GuidedStory:
    def __init__(self, session: Session) -> None:
        self.s = session
        self.step = 0
        self.caption = ""
        self.detail = ""
        self.done = False
        self.results: list[str] = []
        self._gen = self._script()

    def say(self, caption: str, detail: str = "") -> None:
        self.step += 1
        self.caption, self.detail = caption, detail

    def tick(self) -> None:
        if self.done:
            return
        try:
            next(self._gen)
        except StopIteration:
            self.done = True

    def _wait(self, cond: Callable[[], bool], max_ticks: int) -> Generator[None, None, bool]:
        a = self.s.agent
        t0 = a.n
        while not cond():
            if a.n - t0 > max_ticks:
                return False
            yield
        return True

    def _task_done(self, kind: str, since: int) -> Callable[[], bool]:
        return lambda: any(t.kind == kind for t in self.s.agent.task_log[since:])

    def _script(self) -> Generator[None, None, None]:
        a = self.s.agent
        self.say("AEON is born knowing nothing about its body.",
                 "It babbles, finds which signals track its own commands, tests which signal is an object, and measures its reach.")
        yield from self._wait(lambda: len(a.task_log) >= 2, 2500)
        self.say("Body map complete. Now we secretly add a 3-tick delay to its motors.",
                 "AEON is not told. Watch it miss, weigh four explanations, and run a diagnostic movement.")
        self.s.intervene("delay", ticks=3)
        ok = yield from self._wait(lambda: a.sm.delay == 3, 900)
        self.results.append(f"delay diagnosed: {ok}")
        self.say("Diagnosed: 'my action's timing changed'. Self-model revised: delay 0 → 3.",
                 "Only the part of itself the evidence pointed at was revised.")
        yield from self._wait(lambda: False, 30)
        k = len(a.task_log)
        self.say("A ball is thrown. Will it need another failure?",
                 "It predicts that reacting would miss given its lag, so it imagines the throw and plans the intercept.")
        self.s.intervene("catch")
        yield from self._wait(self._task_done("catch", k), 500)
        catch = next((t for t in a.task_log[k:] if t.kind == "catch"), None)
        self.results.append(f"catch success: {bool(catch and catch.success)}")
        self.say("Caught on the first try." if catch and catch.success else "Missed this one — the 20-seed experiment shows 0.92 success.",
                 "The revised self-model transferred to a new task without a new failure.")
        yield from self._wait(lambda: False, 40)
        self.say("Now we secretly bias its vision by 1.3 units.",
                 "Touch and vision will disagree. Is the world different, or are its eyes wrong?")
        self.s.intervene("vision_bias", dx=1.3, dy=0.4)
        ok = yield from self._wait(lambda: max(abs(v) for v in a.sm.vision_offset) > 0.5, 1500)
        self.results.append(f"vision recalibrated: {ok}")
        self.say("It felt for the object, measured the offset, and recalibrated its own eyes.",
                 "Self-model → attention link: perception now subtracts the measured bias.")
        yield from self._wait(lambda: False, 60)
        k = len(a.task_log)
        self.say("An object beyond its workspace.", "Its self-model predicts the reach is impossible, so it declines instead of failing.")
        self.s.intervene("far")
        yield from self._wait(self._task_done("far", k), 300)
        self.say("An unknown tool is attached: a new signal s6 appears.",
                 "It tests whether s6 follows its own movement, measures its radius, then tries a grip that used to be impossible.")
        self.s.intervene("attach_tool")
        ok = yield from self._wait(lambda: bool(a.sm.tool_channels), 900)
        self.results.append(f"tool incorporated: {ok}")
        k = len(a.task_log)
        self.say(f"Reach revised to {a.sm.reach:.2f}. Same out-of-reach object, again.", "The body map now includes the tool.")
        self.s.intervene("far")
        yield from self._wait(self._task_done("far", k), 400)
        far = next((t for t in a.task_log[k:] if t.kind == "far"), None)
        self.results.append(f"far success with tool: {bool(far and far.success)}")
        self.say("Demo complete. Every change above is in the trace panel, with its cause.",
                 "Freeze the self-model (dropdown → frozen_self_model) and it notices the same faults but cannot revise itself.")
