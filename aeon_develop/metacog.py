"""Thinking as an action: a contextual value estimate per cognitive option."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from .plasticity import BoundedParam, Trace

THOUGHTS = ("act", "observe_again", "recall", "imagine", "consult_llm")
TICK_COST = {"act": 0, "observe_again": 5, "recall": 0, "imagine": 0, "consult_llm": 3}
COMPUTE_COST = {"act": 0, "observe_again": 0, "recall": 1, "imagine": 1, "consult_llm": 2}


@dataclass
class ThoughtRecord:
    context: str
    option: str
    predicted_benefit: float
    realized: float | None = None


class Metacognition:
    def __init__(self, trace: Trace, rng: random.Random, epsilon: float = 0.12) -> None:
        self.trace = trace
        self.rng = rng
        self.epsilon = epsilon
        self.values: dict[str, dict[str, BoundedParam]] = {}
        self.counts: dict[str, dict[str, int]] = {}
        self.history: list[ThoughtRecord] = []

    def _row(self, context: str, options: tuple[str, ...]) -> dict[str, BoundedParam]:
        row = self.values.setdefault(context, {})
        counts = self.counts.setdefault(context, {})
        for o in options:
            if o not in row:
                row[o] = BoundedParam(f"metacog.{context}.{o}", 0.5, -1.0, 1.0, 0.25, self.trace)
                counts[o] = 0
        return row

    def choose(self, context: str, options: tuple[str, ...]) -> tuple[str, float]:
        row = self._row(context, options)
        counts = self.counts[context]
        untried = [o for o in options if counts[o] == 0]
        if untried and self.rng.random() < 0.5:
            option = self.rng.choice(untried)
        elif self.rng.random() < self.epsilon:
            option = self.rng.choice(options)
        else:
            option = max(options, key=lambda o: float(row[o]))
        base = float(row[options[0]])
        predicted = float(row[option]) - base
        self.history.append(ThoughtRecord(context, option, predicted))
        return option, predicted

    def update(self, context: str, option: str, utility: float) -> None:
        row = self.values[context]
        self.counts[context][option] += 1
        n = self.counts[context][option]
        row[option].nudge(utility, max(0.2, 1.0 / n), "value-update", f"{context}:{option} utility={utility:.2f}")
        for rec in reversed(self.history):
            if rec.context == context and rec.option == option and rec.realized is None:
                base_options = list(row)
                rec.realized = utility - float(row[base_options[0]])
                break

    def table(self) -> dict[str, dict[str, Any]]:
        return {
            ctx: {o: {"value": round(float(p), 3), "n": self.counts[ctx][o]} for o, p in row.items()}
            for ctx, row in self.values.items()
        }

    def calibration(self) -> float | None:
        pairs = [(r.predicted_benefit, r.realized) for r in self.history if r.realized is not None and r.option != "act"]
        if len(pairs) < 5:
            return None
        xs, ys = zip(*pairs)
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        sxy = sum((x - mx) * (y - my) for x, y in pairs)
        sxx = sum((x - mx) ** 2 for x in xs)
        syy = sum((y - my) ** 2 for y in ys)
        if sxx < 1e-9 or syy < 1e-9:
            return None
        return sxy / (sxx * syy) ** 0.5


class GenericAdvisor:
    """Stand-in for an LLM: fluent, generic, and blind to this body's hidden state."""

    name = "generic-llm-stub"

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng

    def suggest(self, hypotheses: list[str], narration: list[str]) -> tuple[str, str]:
        label = "world_changed" if self.rng.random() < 0.6 else self.rng.choice(hypotheses)
        return label, f"Most likely the environment changed ({label}). Try moving directly to the object again."
