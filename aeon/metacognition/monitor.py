from __future__ import annotations

from aeon.core.contracts import Candidate, ControlSignal, MetacognitiveReport


class MetacognitiveMonitor:
    def assess(
        self, text: str, workspace: list[Candidate], memory_count: int, iteration: int
    ) -> MetacognitiveReport:
        evidence = min(1.0, (memory_count * 0.14) + (len(workspace) * 0.16))
        contradiction = [c.candidate_id for c in workspace if c.contradiction_strength > 0.35]
        difficulty = min(0.95, 0.25 + len(text.split()) / 180)
        predicted = max(0.1, min(0.92, 0.82 - difficulty * 0.35 + evidence * 0.3))
        signal = ControlSignal.CONTINUE
        if contradiction and iteration == 1:
            signal = ControlSignal.VERIFY
        elif evidence < 0.15 and "evidence" in text.lower():
            signal = ControlSignal.RETRIEVE
        elif predicted < 0.35:
            signal = ControlSignal.REQUEST_CLARIFICATION
        return MetacognitiveReport(
            predicted_success=round(predicted, 3),
            task_difficulty=round(difficulty, 3),
            uncertainty_type="epistemic" if evidence < 0.5 else "mixed",
            evidence_sufficiency=round(evidence, 3),
            contradictions=contradiction,
            strategy="evidence-grounded recurrent synthesis",
            control_signal=signal,
            confidence=round(predicted * (0.75 + evidence * 0.25), 3),
            falsification_conditions=[
                "runtime trace contradicts self-report",
                "replication fails",
                "ablation shows no causal dependence",
            ],
        )
