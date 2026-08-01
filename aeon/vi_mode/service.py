from __future__ import annotations

from aeon.core.contracts import MemoryRecord, new_id, utc_now
from aeon.storage.base import Storage


class VIMode:
    STAGES = [
        "stabilize",
        "memory_replay",
        "contradiction_inspection",
        "distant_association",
        "counterfactual",
        "hypothesis",
        "counterargument",
        "prediction",
        "verification_request",
        "quarantine",
    ]

    def __init__(self, storage: Storage) -> None:
        self.storage = storage

    def run(self, prompt: str, memories: list[MemoryRecord]) -> dict[str, object]:
        record = {
            "hypothesis_id": new_id("hyp"),
            "created_at": utc_now().isoformat(),
            "prompt": prompt,
            "stages": self.STAGES,
            "selected_memories": [m.memory_id for m in memories[:5]],
            "hypothesis": f"Quarantined possibility derived from reflective processing: {prompt[:240]}",
            "counterarguments": [
                "May be produced by language-model priors",
                "May not depend causally on persistent architecture",
            ],
            "predictions": ["Ablation should measurably reduce recurrence-sensitive performance"],
            "verification_status": "pending",
            "quarantine_status": "QUARANTINED",
            "canonical_belief_update": False,
        }
        self.storage.write_record("hypotheses", record)
        return record
