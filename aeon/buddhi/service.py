from aeon.core.contracts import Belief, EpistemicClass, MetacognitiveReport


class Buddhi:
    def evaluate(
        self, proposition: str, evidence: list[str], report: MetacognitiveReport, origin: str
    ) -> tuple[Belief, bool]:
        classification = EpistemicClass.INFERENCE if evidence else EpistemicClass.HYPOTHESIS
        belief = Belief(
            proposition=proposition,
            classification=classification,
            confidence=report.confidence,
            evidence=evidence,
            assumptions=["telemetry is intact"],
            falsification_conditions=report.falsification_conditions,
            origin=origin,
        )
        approved = (
            bool(evidence) and report.evidence_sufficiency >= 0.3 and not report.contradictions
        )
        return belief, approved
