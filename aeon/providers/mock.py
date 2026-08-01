from __future__ import annotations

import hashlib
import json
import random
import time

from aeon.providers.base import ModelRequest, ModelResponse, ProviderCapabilities


class MockProvider:
    provider_name = "mock"
    capabilities = ProviderCapabilities(supports_json_schema=True, supports_token_usage=True)

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed

    @staticmethod
    def _stable(value):
        if isinstance(value, dict):
            return {
                key: MockProvider._stable(item)
                for key, item in sorted(value.items())
                if not key.endswith("_id") and key not in {"created_at", "observed_at"}
            }
        if isinstance(value, list):
            return [MockProvider._stable(item) for item in value]
        return value

    async def generate(self, request: ModelRequest) -> ModelResponse:
        started = time.perf_counter()
        stable_state = json.dumps(
            self._stable(request.structured_state), sort_keys=True, default=str
        )
        digest = hashlib.sha256(f"{self.seed}:{request.prompt}:{stable_state}".encode()).hexdigest()
        rng = random.Random(int(digest[:16], 16))
        evidence = request.structured_state.get("evidence", [])
        focus = request.structured_state.get("focus", request.prompt[:80])
        confidence = 0.55 + rng.random() * 0.25
        text = (
            f"AEON assessment: {focus}. "
            f"I distinguish this generated synthesis from {len(evidence)} retrieved evidence item(s). "
            f"Current calibrated confidence: {confidence:.2f}. "
            "This output is an experimentally observable response, not evidence of phenomenal consciousness."
        )
        return ModelResponse(
            text=text,
            provider=self.provider_name,
            model="aeon-deterministic-mock-v1",
            usage={"input_tokens": len(request.prompt.split()), "output_tokens": len(text.split())},
            latency_ms=(time.perf_counter() - started) * 1000,
            metadata={"seed": self.seed, "digest": digest, "confidence": confidence},
        )

    async def health_check(self) -> dict[str, object]:
        return {"healthy": True, "provider": self.provider_name, "deterministic": True}
