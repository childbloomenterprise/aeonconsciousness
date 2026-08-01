from __future__ import annotations

from aeon.core.contracts import new_id, utc_now


class WorldModel:
    def __init__(self) -> None:
        self.entities: dict[str, dict[str, object]] = {}
        self.predictions: list[dict[str, object]] = []

    def interpret(self, text: str) -> dict[str, object]:
        state = {
            "state_id": new_id("world"),
            "observed_at": utc_now().isoformat(),
            "external_input": text,
            "uncertainty": 0.35,
            "causal_links": [],
        }
        self.entities[state["state_id"]] = state
        return state

    def predict(self, proposition: str, probability: float) -> dict[str, object]:
        record = {
            "prediction_id": new_id("pred"),
            "proposition": proposition,
            "probability": probability,
            "status": "pending",
        }
        self.predictions.append(record)
        return record
