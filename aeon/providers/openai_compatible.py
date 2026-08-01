from __future__ import annotations

import time

import httpx

from aeon.providers.base import ModelRequest, ModelResponse, ProviderCapabilities


class OpenAICompatibleProvider:
    provider_name = "openai_compatible"
    capabilities = ProviderCapabilities(
        supports_system_prompt=True, supports_tool_calls=True, supports_json_schema=True
    )

    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.base_url, self.api_key, self.model = base_url.rstrip("/"), api_key, model

    async def generate(self, request: ModelRequest) -> ModelResponse:
        started = time.perf_counter()
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.prompt},
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        return ModelResponse(
            text=data["choices"][0]["message"]["content"],
            provider=self.provider_name,
            model=data.get("model", self.model),
            usage=data.get("usage", {}),
            latency_ms=(time.perf_counter() - started) * 1000,
            metadata={"finish_reason": data["choices"][0].get("finish_reason")},
        )

    async def health_check(self) -> dict[str, object]:
        return {"healthy": True, "provider": self.provider_name, "model": self.model}
