from aeon.core.contracts import Candidate


class GlobalWorkspace:
    def __init__(self, capacity: int = 3, enabled: bool = True) -> None:
        self.capacity, self.enabled = capacity, enabled
        self.contents: list[Candidate] = []

    def broadcast(self, winners: list[Candidate]) -> list[Candidate]:
        self.contents = winners[: self.capacity] if self.enabled else []
        return self.contents

    def snapshot(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "capacity": self.capacity,
            "candidate_ids": [c.candidate_id for c in self.contents],
        }
