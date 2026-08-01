from __future__ import annotations

import hashlib
import json
from typing import Any

from aeon.core.contracts import new_id, utc_now
from aeon.storage.base import Storage


CONFIGURATIONS = [
    "PLAIN_LLM",
    "LLM_WITH_CHAT_HISTORY",
    "LLM_WITH_STRUCTURED_MEMORY",
    "RECURRENT_LLM",
    "WORKSPACE_LLM",
    "SELF_MODEL_LLM",
    "METACOGNITIVE_LLM",
    "WITNESS_ENABLED_AEON",
    "FULL_AEON",
]
MODULES = [
    "manas",
    "citta",
    "workspace",
    "recurrence",
    "self_model",
    "metacognition",
    "buddhi",
    "ahamkara",
    "sakshin",
    "vi_mode",
]


class ExperimentEngine:
    def __init__(self, storage: Storage) -> None:
        self.storage = storage

    def create(
        self,
        hypothesis: str,
        configuration: str = "FULL_AEON",
        seed: int = 42,
        ablations: list[str] | None = None,
        interventions: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if configuration not in CONFIGURATIONS:
            raise ValueError("Unknown configuration")
        invalid = set(ablations or []) - set(MODULES)
        if invalid:
            raise ValueError(f"Unknown ablations: {sorted(invalid)}")
        record = {
            "experiment_id": new_id("exp"),
            "created_at": utc_now().isoformat(),
            "hypothesis": hypothesis,
            "configuration": configuration,
            "seed": seed,
            "ablations": ablations or [],
            "interventions": interventions or {},
            "status": "READY",
            "results": None,
        }
        record["integrity_hash"] = hashlib.sha256(
            json.dumps(record, sort_keys=True, default=str).encode()
        ).hexdigest()
        self.storage.write_record("experiments", record)
        return record

    def list(self) -> list[dict[str, Any]]:
        return self.storage.list_records("experiments")
