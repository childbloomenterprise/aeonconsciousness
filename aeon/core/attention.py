from aeon.core.contracts import Candidate


DEFAULT_COEFFICIENTS = {
    "relevance": 1.0,
    "novelty": 0.8,
    "uncertainty": 0.45,
    "contradiction_strength": 0.75,
    "homeostatic_urgency": 0.6,
    "identity_relevance": 0.55,
    "expected_consequence": 0.7,
    "redundancy": -0.8,
    "estimated_noise": -0.9,
}


class Attention:
    def __init__(self, coefficients: dict[str, float] | None = None) -> None:
        self.coefficients = coefficients or DEFAULT_COEFFICIENTS

    def score(self, candidate: Candidate) -> Candidate:
        breakdown = {
            name: getattr(candidate, name) * weight for name, weight in self.coefficients.items()
        }
        candidate.score_breakdown = {key: round(value, 4) for key, value in breakdown.items()}
        candidate.salience = round(sum(breakdown.values()), 4)
        return candidate

    def compete(
        self, candidates: list[Candidate], capacity: int
    ) -> tuple[list[Candidate], list[Candidate]]:
        scored = sorted(
            (self.score(c) for c in candidates), key=lambda c: (-c.salience, c.candidate_id)
        )
        return scored[:capacity], scored[capacity:]
