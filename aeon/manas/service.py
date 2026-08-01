from __future__ import annotations

import hashlib
import random

from aeon.core.contracts import Candidate


class Manas:
    TYPES = ("interpretation", "hypothesis", "counterfactual", "strategy", "question", "action")

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed

    def generate(
        self, cycle_id: str, text: str, memory_refs: list[str], count: int = 6
    ) -> list[Candidate]:
        # Random identifiers label a run but must never influence deterministic cognition.
        digest = hashlib.sha256(f"{self.seed}:{text}".encode()).hexdigest()
        rng = random.Random(int(digest[:16], 16))
        templates = [
            "Interpret the request literally and identify measurable claims",
            "Retrieve relevant prior evidence before forming a conclusion",
            "Generate an alternative explanation that could falsify the leading view",
            "Assess identity relevance and distinguish provider output from AEON state",
            "Check whether uncertainty warrants verification or abstention",
            "Form a reversible response strategy and track its predicted consequence",
        ]
        candidates: list[Candidate] = []
        for index in range(count):
            candidates.append(
                Candidate(
                    cycle_id=cycle_id,
                    content=f"{templates[index % len(templates)]}: {text[:180]}",
                    candidate_type=self.TYPES[index % len(self.TYPES)],
                    novelty=round(rng.uniform(0.25, 0.95), 4),
                    relevance=round(rng.uniform(0.45, 1.0), 4),
                    uncertainty=round(rng.uniform(0.1, 0.8), 4),
                    contradiction_strength=round(rng.uniform(0.0, 0.45), 4),
                    identity_relevance=round(rng.uniform(0.0, 0.6), 4),
                    expected_consequence=round(rng.uniform(0.2, 0.8), 4),
                    redundancy=round(rng.uniform(0.0, 0.35), 4),
                    estimated_noise=round(rng.uniform(0.0, 0.25), 4),
                    provenance=["external_input", *memory_refs],
                )
            )
        return candidates
