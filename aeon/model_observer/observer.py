from __future__ import annotations

import hashlib
from typing import Any

from aeon.core.contracts import new_id, utc_now
from aeon.providers.base import ModelRequest, ModelResponse
from aeon.storage.base import Storage


class ModelBehaviourObserver:
    def __init__(self, storage: Storage) -> None:
        self.storage = storage

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()

    def record(
        self, cycle_id: str, request: ModelRequest, response: ModelResponse
    ) -> dict[str, Any]:
        trace = {
            "trace_id": new_id("model-trace"),
            "cycle_id": cycle_id,
            "timestamp": utc_now().isoformat(),
            "provider": response.provider,
            "model": response.model,
            "system_context_hash": self._hash(request.system),
            "user_context_hash": self._hash(request.prompt),
            "structured_state_hash": self._hash(str(request.structured_state)),
            "structured_state_keys": sorted(request.structured_state),
            "output_hash": self._hash(response.text),
            "usage": response.usage,
            "latency_ms": response.latency_ms,
            "metadata": response.metadata,
            "hidden_state_access": False,
            "reasoning_label": "external model behaviour",
        }
        self.storage.write_record("model_observer", trace)
        return trace
