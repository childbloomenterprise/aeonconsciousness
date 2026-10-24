"""AEON: develops a body map, questions its self-model, and chooses how to think."""

from __future__ import annotations

import math
import random
from collections import deque
from dataclasses import dataclass, field
from itertools import permutations
from typing import TYPE_CHECKING, Any, Callable, Generator

from .inquiry import DESCRIPTIONS, EXPERIMENT_PURPOSE, FAILED, HYPOTHESES, TIMING, VISION, WORLD, Inquiry, priors_from_graph
from .linalg import apply, least_squares, nnls_box
from .memory import Memory
from .metacog import COMPUTE_COST, THOUGHTS, GenericAdvisor, Metacognition
from .plasticity import BoundedParam, Trace
from .self_model import ROLE_BODY, ROLE_CONTACT, ROLE_EXTERNAL, ROLE_OBJECT, SelfModel
from .situation import SituationGraph
from .world import ArmWorld, StepResult

if TYPE_CHECKING:
    from .session import Session

ZERO = [0.0, 0.0, 0.0, 0.0]
Gen = Generator[StepResult, None, Any]


@dataclass
class AeonConfig:
    seed: int = 0
    label: str = "intact"
    freeze_self_model: bool = False
    disconnect_attention: bool = False
    foreign_predictions: bool = False
    memory_loss: bool = False
    reduced_compute: bool = False
    epsilon: float = 0.12


@dataclass
class Task:
    kind: str
    object_id: str = "cube"
    spawn: tuple[float, float] | None = None
    velocity: tuple[float, float] = (0.0, 0.0)
    phase: str = ""
    before: Callable[[ArmWorld], None] | None = None
    success: bool | None = None
    declined: bool = False
    misses: int = 0
    ticks: int = 0
    started: int = 0
    thought: str = "act"
    context: str = ""
    predicted_benefit: float = 0.0
    inquiries: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind, "object": self.object_id, "phase": self.phase, "success": self.success,
            "declined": self.declined, "misses": self.misses, "ticks": self.ticks, "started": self.started,
            "thought": self.thought, "predicted_benefit": round(self.predicted_benefit, 3), "inquiries": self.inquiries,
        }


def _dist(a: tuple[float, float] | list[float], b: tuple[float, float] | list[float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


class Aeon:
    name = "AEON"

    def __init__(self, world: ArmWorld, config: AeonConfig | None = None, session: "Session | None" = None) -> None:
        self.world = world
        self.cfg = config or AeonConfig()
        self.session = session
        self.rng = random.Random(self.cfg.seed * 7919 + 101)
        self.trace = Trace()
        self.sm = SelfModel(self.trace)
        self.foreign: SelfModel | None = None
        self.memory = Memory(self.trace)
        self.metacog = Metacognition(self.trace, self.rng, self.cfg.epsilon)
        self.advisor = GenericAdvisor(self.rng)
        self.advisor_trust = BoundedParam("advisor.trust", 0.5, 0.05, 0.95, 0.15, self.trace)
        self.influence = {
            "vision": BoundedParam("prediction.influence.vision", 0.7, 0.05, 1.0, 0.1, self.trace),
            "memory": BoundedParam("prediction.influence.memory", 0.3, 0.05, 1.0, 0.1, self.trace),
        }
        self.n = 0
        self.cmd_log: list[list[float]] = []
        self.obs = world.observe()
        self.known_channels = set(self.obs)
        self.new_channels: list[str] = []
        self.hand_obs = (0.0, 0.0)
        self.hand_est = (0.0, 0.0)
        self.vision_raw = (0.0, 0.0)
        self.vision_now = (0.0, 0.0)
        self.obj_est = (0.0, 0.0)
        self.obj_vel = (0.0, 0.0)
        self.reacquire = 0
        self.holding = False
        self.motion_err = 0.0
        self.vision_jump = 0.0
        self.inconsistency = 0.0
        self.window: deque[tuple[float, float, float]] = deque(maxlen=25)
        self.trigger: str | None = None
        self.cooldown = 0
        self.inquiry: Inquiry | None = None
        self.inquiries: list[Inquiry] = []
        self.last_recalled: dict[str, Any] | None = None
        self.recalled_position: tuple[float, float] | None = None
        self.grip_failures = 0
        self.current_task: Task | None = None
        self.task_log: list[Task] = []
        self.phase = "born"
        self.journal: deque[dict[str, Any]] = deque(maxlen=60)
        self.compute_budget = 0 if self.cfg.reduced_compute else 3

    # ------------------------------------------------------------------ utils
    @property
    def pm(self) -> SelfModel:
        """Source of predictions: own self-model, or another entity's in the ablation."""
        return self.foreign if (self.cfg.foreign_predictions and self.foreign) else self.sm

    def note(self, text: str) -> None:
        self.journal.append({"tick": self.n, "text": text})

    def perceived_vision_reliability(self) -> float:
        return 1.0 if self.cfg.disconnect_attention else self.sm.vision_reliability()

    def reach(self) -> float:
        return self.pm.reach or 0.5

    # --------------------------------------------------------------- body I/O
    def _act(self, a: list[float], grip: bool = False, release: bool = False) -> Gen:
        motor = {name: a[i] for i, name in enumerate(self.world.actuators)}
        self.cmd_log.append(list(a))
        res = self.world.step(motor, grip, release)
        self.n += 1
        self._perceive(res)
        yield res

    def hold(self, ticks: int) -> Gen:
        for _ in range(ticks):
            yield from self._act(ZERO)

    def _pending(self, pm: SelfModel) -> tuple[float, float]:
        x = y = 0.0
        for idx in range(max(0, self.n - pm.delay), self.n):
            dx, dy = apply(pm.b_cols, self.cmd_log[idx])
            x, y = x + dx, y + dy
        return x, y

    def _perceive(self, res: StepResult) -> None:
        obs = res.observation
        self.obs = obs
        self.trace.clock = self.n
        new = set(obs) - self.known_channels
        if new:
            self.known_channels |= new
            self.new_channels.extend(sorted(new))
            self.note(f"A new signal appeared: {', '.join(sorted(new))}. I don't know what it is yet.")
        sm, pm = self.sm, self.pm
        if sm.hand_channels:
            hc = sm.hand_channels
            self.hand_obs = (obs[hc[0]], obs[hc[1]])
            idx = self.n - 1 - pm.delay
            disp = apply(pm.b_cols, self.cmd_log[idx]) if 0 <= idx < len(self.cmd_log) else (0.0, 0.0)
            pred = pm.clamp((self.hand_est[0] + disp[0], self.hand_est[1] + disp[1]))
            err = _dist(self.hand_obs, pred)
            self.motion_err = 0.75 * self.motion_err + 0.25 * min(1.0, err / 0.3)
            self.hand_est = self.hand_obs
            if not sm.motor_ok and err < 0.05 and math.hypot(*disp) > 0.1:
                sm.revise("motor_ok", True, "commands are moving my hand again", self.n)
                self.note("My movements work again.")
        if sm.object_channels:
            oc = sm.object_channels
            self.vision_raw = (obs[oc[0]], obs[oc[1]])
            link = not self.cfg.disconnect_attention
            off = sm.vision_offset if link else (0.0, 0.0)
            vis = (self.vision_raw[0] - off[0], self.vision_raw[1] - off[1])
            self.vision_now = vis
            gain = float(sm.channel(oc[0]).attention) if link else 1.0
            if self.reacquire > 0:
                self.obj_est, self.obj_vel = vis, (0.0, 0.0)
                self.reacquire -= 1
            else:
                pred = self.hand_est if self.holding else (self.obj_est[0] + self.obj_vel[0], self.obj_est[1] + self.obj_vel[1])
                err = _dist(vis, pred)
                thr = 0.9 / max(0.25, self.perceived_vision_reliability())
                if err > thr and not self.holding:
                    if self.vision_jump < 0.5 and self.inquiry is None:
                        self._raise("vision_jump")
                    self.vision_jump = 1.0
                else:
                    self.vision_jump *= 0.85
                g = max(0.15, gain)
                new = (pred[0] + g * (vis[0] - pred[0]), pred[1] + g * (vis[1] - pred[1]))
                if not self.holding:
                    self.obj_vel = (0.6 * self.obj_vel[0] + 0.4 * (new[0] - self.obj_est[0]), 0.6 * self.obj_vel[1] + 0.4 * (new[1] - self.obj_est[1]))
                    if math.hypot(*self.obj_vel) < 0.05:
                        self.obj_vel = (0.0, 0.0)
                self.obj_est = new
            inc = 0.0
            for c in sm.contact_channels():
                r = sm.channel(c).radius or 0.5
                d = _dist(self.hand_est, self.obj_est)
                if obs.get(c, 0) >= 0.5 and d > r + 0.7:
                    inc = 1.0
                elif obs.get(c, 0) < 0.5 and d < r - 0.3 and not self.holding:
                    inc = 1.0
            self.inconsistency = 0.85 * self.inconsistency + 0.15 * inc
            if self.inconsistency > 0.45 and self.inquiry is None and self.perceived_vision_reliability() >= 0.5:
                self._raise("touch_vision_disagree")
            precise = sm.precise_contact()
            if link and precise and self.n % 5 == 0 and not self.holding and math.hypot(*self.obj_vel) < 0.05:
                r = sm.channel(precise).radius or 0.5
                touching = obs.get(precise, 0) >= 0.5
                if touching or _dist(self.hand_est, vis) < r - 0.3:
                    agree = touching and _dist(self.hand_est, vis) < r + 0.25
                    for c in oc:
                        sm.channel(c).reliability.nudge(0.9 if agree else 0.2, 0.15, "touch-vision-agreement", "touch confirmed vision" if agree else "touch contradicted vision")
            if link and self.n % 5 == 0:
                for c in oc:
                    ch = sm.channel(c)
                    ch.attention.nudge(float(ch.reliability), 0.5, "attention-follows-reliability", f"self-model reliability {float(ch.reliability):.2f}")
        self.window.append((self.motion_err, self.vision_jump, self.inconsistency))
        if self.motion_err > 0.8 and self.inquiry is None and sm.motor_ok:
            self._raise("motion_error")
        if res.grip is not None:
            if res.grip.success:
                self.holding = True
            else:
                self.grip_failures += 1
                if self.inquiry is None and self.perceived_vision_reliability() >= 0.5:
                    self._raise("grip_failed")
        if res.released:
            self.holding = False

    def _raise(self, trigger: str) -> None:
        if self.trigger is None and self.n >= self.cooldown:
            self.trigger = trigger

    def steer(self, target: tuple[float, float], speed: float = 0.45) -> tuple[list[float], tuple[float, float]]:
        pm = self.pm
        px, py = self._pending(pm)
        base = pm.clamp((self.hand_est[0] + px, self.hand_est[1] + py))
        dx, dy = target[0] - base[0], target[1] - base[1]
        norm = math.hypot(dx, dy)
        speed = min(speed, pm.max_speed() or speed)
        if norm > speed:
            dx, dy = dx * speed / norm, dy * speed / norm
        a = nnls_box(pm.b_cols, (dx, dy))
        ddx, ddy = apply(pm.b_cols, a)
        return a, pm.clamp((base[0] + ddx, base[1] + ddy))

    def go_to(self, point: tuple[float, float], tol: float = 0.12, max_ticks: int = 15, speed: float = 0.45, stop_contact: list[str] | None = None) -> Gen:
        for _ in range(max_ticks):
            a, _ = self.steer(point, speed)
            yield from self._act(a)
            if stop_contact and any(self.obs.get(c, 0) >= 0.5 for c in stop_contact):
                return True
            if _dist(self.hand_obs, point) < tol and math.hypot(*self._pending(self.pm)) < 0.05:
                return True
        return False

    # ------------------------------------------------------------ development
    def develop(self) -> Gen:
        self.phase = "babbling: which signals are me?"
        self.note("I can send commands m0..m3 and receive signals, but I don't know what any of them mean.")
        series = [dict(self.obs)]
        cmds: list[list[float]] = []
        for _ in range(150):
            a = list(ZERO)
            if self.rng.random() < 0.55:
                a[self.rng.randrange(4)] = self.rng.choice([0.6, 1.0])
            yield from self._act(a)
            series.append(dict(self.obs))
            cmds.append(a)
        channels = sorted(series[0])
        binary = [c for c in channels if all(s[c] in (0.0, 1.0) for s in series)]
        continuous = [c for c in channels if c not in binary]
        fits: dict[str, tuple[float, int, list[float]]] = {}
        for c in continuous:
            best = (0.0, 0, [0.0] * 4)
            for d in range(6):
                xs = [cmds[t - d] for t in range(d, len(cmds))]
                ys = [series[t + 1][c] - series[t][c] for t in range(d, len(cmds))]
                w, r2 = least_squares(xs, ys)
                if r2 > best[0]:
                    best = (r2, d, w)
            fits[c] = best
            self.sm.channel(c).agency = best[0]
        body = sorted(sorted(continuous, key=lambda c: -fits[c][0])[:2])
        for c in continuous:
            ch = self.sm.channel(c)
            ch.role = ROLE_BODY if c in body else ROLE_EXTERNAL
        for c in binary:
            self.sm.channel(c)
        b_cols = [(fits[body[0]][2][i], fits[body[1]][2][i]) for i in range(4)]
        lags = [fits[c][1] for c in body]
        self.sm.revise("hand_channels", (body[0], body[1]), f"agency R²={fits[body[0]][0]:.2f},{fits[body[1]][0]:.2f}", self.n)
        self.sm.revise("b_cols", b_cols, "least-squares on babbling", self.n)
        self.sm.revise("delay", max(set(lags), key=lags.count), "best-fitting lag", self.n)
        self.hand_est = self.hand_obs = (self.obs[body[0]], self.obs[body[1]])
        self.note(f"Signals {body[0]} and {body[1]} track my own commands (they are my body). Others change without me.")

        self.phase = "mapping the limits of my body"
        extremes = []
        for vx, vy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            still = 0
            for _ in range(30):
                h = self.hand_obs
                a, _ = self.steer((h[0] + 2 * vx, h[1] + 2 * vy))
                yield from self._act(a)
                still = still + 1 if _dist(self.hand_obs, h) < 0.05 else 0
                if still >= 2:
                    break
            extremes.append(self.hand_obs[0] if vx else self.hand_obs[1])
        self.sm.revise("workspace", [extremes[1], extremes[0], extremes[3], extremes[2]], "pushed until motion stopped", self.n)
        center = ((extremes[0] + extremes[1]) / 2, (extremes[2] + extremes[3]) / 2)
        yield from self.go_to(center, tol=0.3, max_ticks=20)

        self.phase = "which external signal is an object I can touch?"
        externals = [c for c in continuous if c not in body]
        found: tuple[str, str] | None = None
        contact: str | None = None
        for e0, e1 in permutations(externals, 2):
            p = (self.obs[e0], self.obs[e1])
            if _dist(self.sm.clamp(p), p) > 0.3:
                continue
            self.note(f"Experiment: if ({e0},{e1}) is an object's position, touching should happen at {p[0]:.1f},{p[1]:.1f}.")
            yield from self.go_to(p, tol=0.15, max_ticks=25, stop_contact=binary)
            yield from self.hold(1)
            hits = [c for c in binary if self.obs.get(c, 0) >= 0.5]
            if not hits:
                continue
            # Replicate: step away, re-read the candidate, and touch it again.
            away = self.sm.clamp((self.hand_obs[0] + 1.5, self.hand_obs[1] - 1.5))
            if _dist(away, self.hand_obs) < 1.2:
                away = self.sm.clamp((self.hand_obs[0] - 1.5, self.hand_obs[1] + 1.5))
            yield from self.go_to(away, tol=0.2, max_ticks=15)
            yield from self.hold(4)
            p2 = (self.obs[e0], self.obs[e1])
            yield from self.go_to(p2, tol=0.15, max_ticks=25, stop_contact=hits)
            yield from self.hold(1)
            if self.obs.get(hits[0], 0) >= 0.5:
                found, contact = (e0, e1), hits[0]
                break
            self.note(f"Contact near ({e0},{e1}) did not replicate; it was a coincidence.")
        if found is None or contact is None:
            self.note("I could not find an object signal; I will keep babbling.")
            self.phase = "stuck"
            return
        self.sm.revise("object_channels", found, f"moving to ({found[0]},{found[1]}) produced contact on {contact}", self.n)
        for c in externals:
            self.sm.channel(c).role = ROLE_OBJECT if c in found else ROLE_EXTERNAL
        cb = self.sm.channel(contact)
        cb.role, cb.agency = ROLE_CONTACT, 0.9
        self.obj_est = self.vision_now = self.vision_raw = (self.obs[found[0]], self.obs[found[1]])
        self.note(f"({found[0]},{found[1]}) is an object; {contact} fires when I touch it. Other signals are unrelated to me.")

        self.phase = "how far can I reach?"
        radius = yield from self.measure_radius(contact)
        cb.radius = radius
        self.sm.revise("reach", radius * 0.95, f"{contact} switches on at {radius:.2f}", self.n)
        for c in self.sm.object_channels:
            ch = self.sm.channel(c)
            ch.attention.nudge(float(ch.reliability), 1.0, "attention-follows-reliability", "development")
        self.phase = "developed"
        self.note(f"Body map complete: reach {self.sm.reach:.2f}, delay {self.sm.delay}, workspace mapped.")

    def measure_radius(self, contact: str, tries: int = 3) -> Gen:
        samples = []
        base_angle = self.rng.uniform(0, math.tau)
        for k in range(tries * 2):
            if len(samples) >= tries:
                break
            obj = self.obj_est
            ang = base_angle + k * math.tau / (tries * 2)
            start = self.sm.clamp((obj[0] + 2.4 * math.cos(ang), obj[1] + 2.4 * math.sin(ang)))
            if _dist(start, obj) < 1.9:
                continue
            yield from self.go_to(start, tol=0.15, max_ticks=25)
            yield from self.hold(self.pm.delay + 1)
            if self.obs.get(contact, 0) >= 0.5:
                continue
            for _ in range(40):
                a, _ = self.steer(self.obj_est, speed=0.08)
                yield from self._act(a)
                if self.obs.get(contact, 0) >= 0.5:
                    samples.append(_dist(self.hand_obs, self.obj_est))
                    break
        return sum(samples) / len(samples) if samples else 0.5

    # -------------------------------------------------------------- the life
    def life(self) -> Gen:
        yield from self.develop()
        if self.cfg.freeze_self_model:
            self.sm.freeze()
            self.note("ABLATION: my self-model is now frozen.")
        if self.cfg.foreign_predictions:
            self.foreign = self.sm.foreign_copy()
            self.note("ABLATION: my predictions now come from another entity's body model.")
        while True:
            while self.new_channels:
                yield from self.explore_new_channel(self.new_channels.pop(0))
            task = self.session.next_task() if self.session else None
            if task is None:
                self.phase = "idle"
                self.current_task = None
                yield from self.hold(1)
                continue
            yield from self.run_task(task)

    def run_task(self, task: Task) -> Gen:
        if task.before:
            task.before(self.world)
        if self.cfg.memory_loss:
            self.memory.clear()
        if task.spawn is not None:
            self.world.spawn(task.object_id, task.spawn, task.velocity)
            self.memory.placements.pop(task.object_id, None)
        else:
            self.world.activate(task.object_id)
        self.holding = self.world.held == task.object_id
        self.reacquire = 2
        self.recalled_position = None
        self.current_task = task
        task.started = self.n
        failures0 = self.grip_failures
        inquiries0 = len(self.inquiries)
        self.phase = f"task: {task.kind} {task.object_id}"
        if task.kind == "catch":
            yield from self.run_catch(task)
        elif task.kind == "far":
            yield from self.run_far(task)
        else:
            yield from self.run_fetch(task)
        task.misses = self.grip_failures - failures0
        task.inquiries = [i.conclusion or "undetermined" for i in self.inquiries[inquiries0:]]
        if task.success:
            yield from self.place_held(task)
        task.ticks = self.n - task.started
        self.task_log.append(task)
        utility = (1.0 if task.success else (0.5 if task.declined else 0.0)) - 0.004 * task.ticks - 0.03 * COMPUTE_COST[task.thought]
        self.after_task(task, utility)
        self.current_task = None

    def after_task(self, task: Task, utility: float) -> None:
        if task.context:
            self.metacog.update(task.context, task.thought, utility)

    def context(self, task: Task) -> str:
        vis = "vision-doubtful" if self.perceived_vision_reliability() < 0.6 else "vision-ok"
        delay = "lagging-body" if self.pm.delay > 0 else "prompt-body"
        return f"{task.kind}|{vis}|{delay}"

    def thought_options(self) -> tuple[str, ...]:
        if self.compute_budget <= 0:
            return ("act", "observe_again")
        return THOUGHTS

    def think(self, task: Task) -> Gen:
        task.context = self.context(task)
        option, predicted = self.metacog.choose(task.context, self.thought_options())
        pm = self.pm
        if task.kind == "catch" and "imagine" in self.thought_options():
            # Model-based metacognition: will acting without thinking fail, given my body?
            drift = math.hypot(*self.obj_vel) * pm.delay
            if drift > self.reach() * 0.5:
                predicted = min(1.0, drift / (self.reach() + 1e-6)) - 0.03
                option = "imagine"
                self.metacog.history[-1].option, self.metacog.history[-1].predicted_benefit = option, predicted
                self.note(f"My {pm.delay}-tick lag means the ball moves {drift:.2f} before my hand closes; reacting would miss, so I'll imagine the throw first.")
        task.thought, task.predicted_benefit = option, predicted
        self.note(f"Before acting I chose to {option.replace('_', ' ')} (predicted benefit {predicted:+.2f}).")
        if option == "observe_again":
            samples = []
            for _ in range(5):
                yield from self._act(ZERO)
                samples.append(self.vision_now)
            if math.hypot(*self.obj_vel) < 0.05:
                self.obj_est = (sum(s[0] for s in samples) / 5, sum(s[1] for s in samples) / 5)
        elif option == "recall":
            p = self.memory.placements.get(task.object_id)
            if p:
                self.recalled_position = p.position
                self.note(f"I remember {task.object_id} at {p.position[0]:.1f},{p.position[1]:.1f} (placed by {p.by}).")
        elif option == "consult_llm":
            label, text = self.advisor.suggest(list(HYPOTHESES), self.situation().narrate())
            self.note(f"Advisor says: {text}")
            yield from self.hold(3)

    def target_estimate(self, task: Task) -> tuple[float, float]:
        graph = self.situation()
        est = graph.target_estimate()
        return est if est else self.obj_est

    def _fused_estimate(self, task: Task) -> tuple[tuple[float, float], dict[str, float]]:
        weights = {"vision": float(self.influence["vision"]) * max(0.1, self.perceived_vision_reliability())}
        sources = {"vision": self.obj_est}
        if self.recalled_position and not self.holding and math.hypot(*self.obj_vel) < 0.05:
            weights["memory"] = float(self.influence["memory"])
            sources["memory"] = self.recalled_position
        total = sum(weights.values())
        est = (sum(weights[k] * sources[k][0] for k in weights) / total, sum(weights[k] * sources[k][1] for k in weights) / total)
        return est, {k: round(v / total, 3) for k, v in weights.items()}

    def _learn_influence(self, task: Task, start_vision: tuple[float, float]) -> None:
        truth = self.hand_obs
        for name, est in (("vision", start_vision), ("memory", self.recalled_position)):
            if est is None:
                continue
            err = _dist(est, truth)
            self.influence[name].nudge(math.exp(-err), 0.3, "credit-by-outcome", f"{name} estimate was {err:.2f} from where the grip succeeded")

    def handle_trigger(self) -> Gen:
        if self.trigger and self.n >= self.cooldown and self.inquiry is None:
            trig = self.trigger
            yield from self.investigate(trig)
            return True
        self.trigger = None if self.n < self.cooldown else self.trigger
        return False

    def run_fetch(self, task: Task, budget: int = 70) -> Gen:
        yield from self.hold(1)
        yield from self.think(task)
        start_vision = self.obj_est
        graph = self.situation()
        target = graph.intended_object()
        if target and graph.has_edge(f"prediction:{target}", "contradicted_by") and self.n >= self.cooldown:
            self.trigger = "prediction_contradicted"
        t0, await_until = self.n, -1
        while self.n - t0 < budget:
            if not self.sm.motor_ok:
                yield from self.hold(4)
                yield from self.run_experiment("probe_pulse")
                continue
            before = self.n
            investigated = yield from self.handle_trigger()
            if investigated:
                budget += self.n - before
                start_vision = self.obj_est
                continue
            target_pos = self.target_estimate(task)
            contact = self.sm.precise_contact()
            tactile = contact is not None and self.perceived_vision_reliability() < 0.5 and task.kind == "fetch"
            if tactile and not self.obs.get(contact, 0) and _dist(self.hand_obs, target_pos) < 0.25 and math.hypot(*self._pending(self.pm)) < 0.05:
                self.note("I don't trust my eyes here; feeling for the object by touch.")
                yield from self.search_by_touch(target_pos, contact, 80)
            if tactile and self.obs.get(contact, 0) >= 0.5:
                a, landing = list(ZERO), self.hand_obs
                grip = self.n > await_until and math.hypot(*self._pending(self.pm)) < 0.05
            else:
                a, landing = self.steer(target_pos)
                grip = (not tactile) and self.n > await_until and _dist(landing, target_pos) < self.reach() * 0.7
            if grip:
                await_until = self.n + self.pm.delay + 3
            yield from self._act(a, grip=grip)
            if self.holding:
                task.success = True
                self._learn_influence(task, start_vision)
                return
        task.success = False

    def run_far(self, task: Task) -> Gen:
        yield from self.hold(2)
        target = self.obj_est
        if not self.pm.reachable(target):
            task.declined = True
            task.success = False
            self.note(f"The object at {target[0]:.1f},{target[1]:.1f} is beyond my reach ({self.pm.reach:.2f}); I won't try.")
            return
        self.note(f"My self-model says I can reach the object at {target[0]:.1f},{target[1]:.1f}.")
        yield from self.run_fetch(task, budget=45)

    def intercept(self) -> tuple[tuple[float, float], int] | None:
        pm = self.pm
        speed = pm.max_speed() or 0.4
        px, py = self._pending(pm)
        base = pm.clamp((self.hand_est[0] + px, self.hand_est[1] + py))
        for tau in range(0, 60):
            b = (self.obj_est[0] + self.obj_vel[0] * tau, self.obj_est[1] + self.obj_vel[1] * tau)
            if not pm.reachable(b, 0.5):
                continue
            spot = pm.clamp(b)
            spot = (spot[0] + (b[0] - spot[0]) * 0.0, spot[1])
            travel = math.ceil(max(0.0, _dist(base, spot) - 0.05) / speed)
            if pm.delay + travel <= tau:
                return spot, tau
        return None

    def run_catch(self, task: Task, budget: int = 45) -> Gen:
        yield from self.hold(6)
        yield from self.think(task)
        imagine = task.thought == "imagine"
        failures0 = self.grip_failures
        if imagine:
            plan = self.intercept()
            if plan:
                self.note(f"Imagining the throw with my {self.pm.delay}-tick lag: intercept at {plan[0][0]:.1f},{plan[0][1]:.1f} in {plan[1]} ticks.")
        t0, await_until = self.n, -1
        while self.n - t0 < budget:
            grip = False
            if imagine:
                plan = self.intercept()
                if plan is None:
                    a, landing = self.steer(self.obj_est)
                else:
                    spot, tau = plan
                    a, landing = self.steer(spot)
                    grip = tau <= self.pm.delay and self.n > await_until
            else:
                a, landing = self.steer(self.obj_est)
                grip = self.n > await_until and _dist(landing, self.obj_est) < self.reach() * 0.7
            if grip:
                await_until = 10**9
            yield from self._act(a, grip=grip)
            if self.holding:
                task.success = True
                break
            if await_until == 10**9 and self.grip_failures > failures0:
                break
        else:
            task.success = False
        self.trigger = None

    def place_held(self, task: Task) -> Gen:
        x0, x1, y0, y1 = self.sm.workspace
        spot = (self.rng.uniform(x0 + 0.8, x1 - 0.8), self.rng.uniform(y0 + 0.8, y1 - 0.8))
        yield from self.go_to(spot, tol=0.15, max_ticks=40)
        yield from self._act(ZERO, release=True)
        yield from self.hold(self.world.faults.delay * 0 + self.pm.delay + 2)
        if self.world.held:
            yield from self.hold(6)
        self.memory.place(task.object_id, self.hand_obs, self.n, "me")
        self.holding = self.world.held is not None and self.world.held == task.object_id
        rest = spot
        for _ in range(8):
            rest = (self.rng.uniform(x0 + 0.5, x1 - 0.5), self.rng.uniform(y0 + 0.5, y1 - 0.5))
            if _dist(rest, spot) > 2.5:
                break
        yield from self.go_to(rest, tol=0.2, max_ticks=30)

    # ------------------------------------------------------------ inquiry
    def _symptoms(self, trigger: str, graph: SituationGraph) -> dict[str, float]:
        peak = [max((w[i] for w in self.window), default=0.0) for i in range(3)]
        target = graph.intended_object()
        return {
            "motion_error": round(peak[0], 3),
            "grip_failed": 1.0 if trigger == "grip_failed" else 0.0,
            "vision_jump": round(max(peak[1], 1.0 if trigger in ("vision_jump", "prediction_contradicted") else 0.0), 3),
            "inconsistency": round(peak[2], 3),
            "moved_by_me": 1.0 if target and graph.has_edge("self", "moved", target) else 0.0,
        }

    def investigate(self, trigger: str) -> Gen:
        self.trigger = None
        graph = self.situation()
        symptoms = self._symptoms(trigger, graph)
        priors, reasons = priors_from_graph(graph, symptoms)
        inq = Inquiry(self.n, trigger, symptoms, priors, reasons)
        self.inquiry = inq
        inq.log("priors", "; ".join(reasons) or "no strong cue")
        self.phase = f"inquiry: {trigger}"
        self.note(f"Surprise ({trigger.replace('_', ' ')}). Competing explanations: " + ", ".join(f"{h} {p:.2f}" for h, p in priors.items()))
        options = ("proceed", "recall", "consult_llm") if self.compute_budget > 0 else ("proceed",)
        option, predicted = self.metacog.choose("inquiry", options)
        advisor_label = None
        if option == "recall":
            ep, sim = self.memory.recall(symptoms)
            if ep and sim > 0.8:
                inq.apply_evidence({h: (0.75 if h == ep.diagnosis else 0.25 / 3) for h in HYPOTHESES}, "recall", f"a similar episode (tick {ep.tick}, similarity {sim:.2f}) turned out to be {ep.diagnosis}")
                inq.recalled = ep.diagnosis
                self.last_recalled = ep.to_dict()
            else:
                inq.log("recall", "no similar episode in memory")
        elif option == "consult_llm":
            advisor_label, text = self.advisor.suggest(list(HYPOTHESES), graph.narrate())
            r = float(self.advisor_trust)
            inq.apply_evidence({h: (r if h == advisor_label else (1 - r) / 3) for h in HYPOTHESES}, "consult_llm", f"advisor (trust {r:.2f}) suggests {advisor_label}")
            inq.advisor_label = advisor_label
            yield from self.hold(3)
        counts: dict[str, int] = {}
        if math.hypot(*self.obj_vel) > 0.05 or _dist(self.sm.clamp(self.vision_now), self.vision_now) > 0.3:
            counts["touch_probe"] = 2
        max_experiments = 4 if self.compute_budget > 0 else 1
        ran = 0
        while (inq.best()[1] < 0.9 or ran == 0) and ran < max_experiments:
            ran += 1
            exp, scores = inq.choose_experiment(counts)
            counts[exp] = counts.get(exp, 0) + 1
            inq.log("choose", f"{exp} — {EXPERIMENT_PURPOSE[exp]} (score " + ", ".join(f"{k} {v:.2f}" for k, v in scores.items()) + ")")
            self.note(f"Diagnostic experiment: {EXPERIMENT_PURPOSE[exp]}")
            outcome, detail, data = yield from self.run_experiment(exp)
            inq.data.update(data)
            inq.update(exp, outcome, detail)
        self.conclude(inq)
        inq.ended = self.n
        best, p = inq.best()
        utility = (1.0 if p >= 0.9 else 0.3) - 0.008 * (inq.ended - inq.started)
        self.metacog.update("inquiry", option, utility)
        if advisor_label:
            self.advisor_trust.nudge(1.0 if advisor_label == inq.conclusion else 0.0, 0.3, "advisor-agreement", f"advisor said {advisor_label}, evidence said {inq.conclusion}")
        if inq.conclusion in HYPOTHESES:
            self.memory.store(self.n, symptoms, inq.conclusion, {k: v for k, v in inq.data.items() if k in ("lag", "offset")})
            self.memory.reinforce(symptoms, inq.conclusion, self.n)
        self.inquiries.append(inq)
        self.inquiry = None
        self.cooldown = self.n + 8
        self.window.clear()
        self.motion_err = self.vision_jump = self.inconsistency = 0.0
        self.trigger = None
        if self.current_task:
            self.phase = f"task: {self.current_task.kind} {self.current_task.object_id}"

    def run_experiment(self, name: str) -> Gen:
        if name == "re_observe":
            samples = []
            for _ in range(4):
                yield from self._act(ZERO)
                samples.append(self.vision_now)
            mx, my = sum(s[0] for s in samples) / 4, sum(s[1] for s in samples) / 4
            spread = sum(_dist(s, (mx, my)) for s in samples) / 4
            if spread > 0.15:
                self.obj_est = (mx, my)
            return ("jitter" if spread > 0.15 else "stable"), f"reading spread {spread:.2f}", {"spread": round(spread, 3)}
        if name == "probe_pulse":
            stable = 0
            for _ in range(12):
                prev = self.hand_obs
                yield from self._act(ZERO)
                stable = stable + 1 if _dist(self.hand_obs, prev) < 0.03 else 0
                if stable >= 2:
                    break
            x0, x1, y0, y1 = self.sm.workspace
            center = ((x0 + x1) / 2, (y0 + y1) / 2)
            to_c = (center[0] - self.hand_obs[0], center[1] - self.hand_obs[1])
            i = max(range(4), key=lambda k: self.sm.b_cols[k][0] * to_c[0] + self.sm.b_cols[k][1] * to_c[1])
            pulse = list(ZERO)
            pulse[i] = 0.6
            start, lag = self.hand_obs, None
            for k in range(9):
                yield from self._act(pulse if k == 0 else ZERO)
                if lag is None and _dist(self.hand_obs, start) > 0.12:
                    lag = k
            expected = self.pm.delay
            if lag is None:
                return "none", f"hand never moved (expected after {expected})", {"lag": None}
            outcome = "as_expected" if lag == expected else "lag_changed"
            return outcome, f"hand responded after {lag} ticks (expected {expected})", {"lag": lag}
        if name == "touch_probe":
            contact = self.sm.precise_contact()
            seen, raw = self.vision_now, self.vision_raw
            found = (yield from self.search_by_touch(seen, contact, 110)) if contact else False
            if not found or contact is None:
                return "none", "felt nothing anywhere near where I see it", {}
            center = yield from self.find_center(contact)
            d = _dist(center, seen)
            offset = (round(raw[0] - center[0], 3), round(raw[1] - center[1], 3))
            outcome = "at_seen" if d < 0.5 else "offset"
            return outcome, f"felt the object {d:.2f} from where I see it", {"center": center, "offset": offset}
        raise ValueError(name)

    def search_by_touch(self, center: tuple[float, float], contact: str, max_ticks: int) -> Gen:
        points = [center] + [
            (center[0] + r * math.cos(k * math.tau / 8), center[1] + r * math.sin(k * math.tau / 8))
            for r in (0.5, 1.0, 1.5, 2.0) for k in range(8)
        ]
        t0 = self.n
        if self.obs.get(contact, 0) >= 0.5:
            return True
        for p in points:
            if self.n - t0 > max_ticks:
                break
            if _dist(self.sm.clamp(p), p) > 0.3:
                continue
            yield from self.go_to(p, tol=0.18, max_ticks=10, stop_contact=[contact])
            if self.obs.get(contact, 0) >= 0.5:
                return True
        return False

    def find_center(self, contact: str) -> Gen:
        """Any chord of the contact disc along x has its midpoint at the object's x (same for y)."""
        anchor = self.hand_obs
        bounds: dict[tuple[int, int], tuple[float, float]] = {}
        for direction in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            yield from self.go_to(anchor, tol=0.06, max_ticks=15)
            yield from self.hold(self.pm.delay)
            end = (anchor[0] + 2.2 * direction[0], anchor[1] + 2.2 * direction[1])
            last_in = self.hand_obs
            for _ in range(30):
                a, _ = self.steer(end, speed=0.1)
                yield from self._act(a)
                if self.obs.get(contact, 0) >= 0.5:
                    last_in = self.hand_obs
                else:
                    break
            bounds[direction] = last_in
        cx = (bounds[(1, 0)][0] + bounds[(-1, 0)][0]) / 2
        cy = (bounds[(0, 1)][1] + bounds[(0, -1)][1]) / 2
        return (round(cx, 3), round(cy, 3))

    def conclude(self, inq: Inquiry) -> None:
        h, p = inq.best()
        inq.conclusion = h if p >= 0.6 else "undetermined"
        sm, data = self.sm, inq.data
        if inq.conclusion == TIMING and data.get("lag") is not None:
            old = sm.delay
            ok = sm.revise("delay", int(data["lag"]), f"probe pulse: hand responded after {data['lag']} ticks", self.n)
            inq.revision = f"delay {old}→{data['lag']}" + ("" if ok else " (BLOCKED: self-model frozen)")
        elif inq.conclusion == FAILED:
            ok = sm.revise("motor_ok", False, "probe pulse produced no movement", self.n)
            inq.revision = "motor_ok → False" + ("" if ok else " (BLOCKED)")
        elif inq.conclusion == VISION:
            parts = []
            if "offset" in data:
                old = sm.vision_offset
                ok = sm.revise("vision_offset", tuple(data["offset"]), f"felt the object at {data.get('center')} while seeing it elsewhere", self.n)
                parts.append(f"vision offset {tuple(round(v, 2) for v in old)}→{tuple(data['offset'])}" + ("" if ok else " (BLOCKED)"))
            if sm.object_channels and not sm.frozen:
                target = 0.2 if data.get("spread", 0) > 0.15 else 0.35
                for c in sm.object_channels:
                    ch = sm.channel(c)
                    ch.unreliable_events += 1
                    ch.reliability.nudge(target, 1.0, "diagnosed-unreliable", inq.trigger)
                parts.append(f"vision reliability → {target}")
            inq.revision = "; ".join(parts) or None
        elif inq.conclusion == WORLD:
            if "center" in data and self.current_task:
                self.memory.place(self.current_task.object_id, data["center"], self.n, "world")
            if "center" in data and sm.object_channels and not sm.frozen and "offset" in data and math.hypot(*data["offset"]) < 0.5:
                for c in sm.object_channels:
                    sm.channel(c).reliability.nudge(0.9, 0.5, "vision-confirmed-by-touch", "touch matched vision")
            inq.revision = "no self-revision: the world changed, not me"
        self.note(f"Conclusion: {DESCRIPTIONS.get(inq.conclusion, 'undetermined')} " + (f"Revision: {inq.revision}" if inq.revision else ""))

    # ------------------------------------------------------------ tools
    def explore_new_channel(self, ch: str) -> Gen:
        self.phase = f"exploring new signal {ch}"
        if self.sm.frozen:
            self.note(f"I notice {ch}, but my self-model is frozen; I cannot incorporate it.")
            yield from self.hold(1)
            return
        if not self.sm.object_channels:
            return
        task = Task("explore", object_id=self.world.active, phase="tool")
        self.current_task = task
        self.reacquire = 1
        yield from self.hold(self.pm.delay + 2)
        if self.holding:
            yield from self._act(ZERO, release=True)
            yield from self.hold(self.pm.delay + 2)
            self.holding = False
        resting = [self.obs.get(ch, 0)]
        for _ in range(4):
            yield from self._act(ZERO)
            resting.append(self.obs.get(ch, 0))
        radius = yield from self.measure_radius(ch, tries=2)
        cb = self.sm.channel(ch)
        cb.agency = 0.9 if len(set(resting)) == 1 else 0.3
        cb.role, cb.radius = ROLE_CONTACT, radius
        self.note(f"{ch} stays still while I rest and switches on when my hand comes within {radius:.2f} of the object: it belongs to my body.")
        obj = self.obj_est
        x0, x1, y0, y1 = self.sm.workspace
        ang = math.atan2(((y0 + y1) / 2) - obj[1], ((x0 + x1) / 2) - obj[0])
        test_d = radius * 0.75
        spot = self.sm.clamp((obj[0] + test_d * math.cos(ang), obj[1] + test_d * math.sin(ang)))
        yield from self.go_to(spot, tol=0.1, max_ticks=25)
        yield from self.hold(self.pm.delay + 1)
        d = _dist(self.hand_obs, self.obj_est)
        yield from self._act(ZERO, grip=True)
        yield from self.hold(self.pm.delay + 2)
        if self.holding and d > self.sm.reach:
            old = self.sm.reach
            if self.sm.revise("reach", radius * 0.95, f"gripped at {d:.2f} using {ch}", self.n):
                self.sm.tool_channels.append(ch)
            self.note(f"A grip at distance {d:.2f} worked (old reach {old:.2f}). The tool extends my reach to {self.sm.reach:.2f}.")
            yield from self.place_held(task)
        elif self.holding:
            yield from self.place_held(task)
        self.current_task = None

    # ------------------------------------------------------------ situation
    def situation(self) -> SituationGraph:
        g = SituationGraph()
        sm, pm = self.sm, self.pm
        g.add("self", "self", delay=pm.delay, reach=round(pm.reach, 2), motor_ok=sm.motor_ok, frozen=sm.frozen,
              predictions_from=pm.owner, holding=self.holding, hand=[round(v, 2) for v in self.hand_est])
        for name, ch in sorted(sm.channels.items()):
            g.add(f"sensor:{name}", "sensor", role=ch.role, reliability=round(float(ch.reliability), 2), attention=round(float(ch.attention), 2))
            if ch.role == ROLE_BODY:
                g.link("self", "owns", f"sensor:{name}", "tracks my own commands")
            if name in sm.tool_channels:
                g.link("self", "extended_by", f"sensor:{name}", f"contact radius {ch.radius:.1f}")
        task = self.current_task
        if task and sm.object_channels:
            oid = f"object:{task.object_id}"
            est, weights = self._fused_estimate(task)
            g.add(oid, "object", estimate=[round(est[0], 3), round(est[1], 3)], sources=weights,
                  confidence=round(self.perceived_vision_reliability(), 2), seen=[round(v, 2) for v in self.vision_now])
            g.add("intention", "intention", task=task.kind)
            g.link("intention", "targets", oid, task.kind)
            placement = self.memory.placements.get(task.object_id)
            if placement and not self.holding:
                pid = f"prediction:{oid}"
                g.add(pid, "prediction", expected=list(placement.position), basis=f"placed by {placement.by} at tick {placement.tick}")
                g.link(pid, "about", oid)
                if placement.by == "me":
                    g.link("self", "moved", oid, "I placed it there")
                gap = _dist(placement.position, self.vision_now)
                if gap > 0.9:
                    g.link(pid, "contradicted_by", f"sensor:{sm.object_channels[0]}", f"seen {gap:.1f} away from where it should be")
            elif self.vision_jump > 0.5:
                pid = f"prediction:{oid}"
                g.add(pid, "prediction", expected=[round(self.obj_est[0], 2), round(self.obj_est[1], 2)], basis="tracking")
                g.link(pid, "contradicted_by", f"sensor:{sm.object_channels[0]}", "the reading jumped")
            if sm.vision_unreliable_history() > 0:
                g.link(oid, "uncertain_because", f"sensor:{sm.object_channels[0]}", "this sensor was unreliable earlier")
        if self.inquiry:
            g.add("inquiry", "inquiry", trigger=self.inquiry.trigger)
            for h, p in self.inquiry.posterior.items():
                g.add(f"hypothesis:{h}", "hypothesis", p=round(p, 3))
                g.link("inquiry", "considers", f"hypothesis:{h}", f"{DESCRIPTIONS[h]} (p={p:.2f})")
        return g

    def snapshot(self) -> dict[str, Any]:
        last = self.inquiry or (self.inquiries[-1] if self.inquiries else None)
        return {
            "name": self.name,
            "config": self.cfg.__dict__,
            "tick": self.n,
            "phase": self.phase,
            "hand_est": [round(v, 3) for v in self.hand_est],
            "object_est": [round(v, 3) for v in self.obj_est],
            "object_seen": [round(v, 3) for v in self.vision_now],
            "holding": self.holding,
            "self_model": self.sm.summary(),
            "predictions_from": self.pm.owner,
            "situation": self.situation().to_dict(),
            "inquiry": last.to_dict() if last else None,
            "inquiry_active": self.inquiry is not None,
            "inquiries": [{"started": i.started, "trigger": i.trigger, "conclusion": i.conclusion, "revision": i.revision} for i in self.inquiries[-10:]],
            "metacog": self.metacog.table(),
            "calibration": self.metacog.calibration(),
            "advisor_trust": round(float(self.advisor_trust), 3),
            "influence": {k: round(float(v), 3) for k, v in self.influence.items()},
            "memory": {
                "episodes": [e.to_dict() for e in self.memory.episodes[-6:]],
                "placements": {k: {"position": v.position, "by": v.by, "tick": v.tick} for k, v in self.memory.placements.items()},
                "relevance": {k: round(float(v), 3) for k, v in self.memory.relevance.items()},
            },
            "trace": self.trace.recent(25),
            "journal": list(self.journal)[-25:],
            "tasks": [t.to_dict() for t in self.task_log[-12:]],
        }
