from __future__ import annotations

import time

import httpx

from aeon.providers.base import ModelRequest, ModelResponse, ProviderCapabilities


class AnthropicProvider:
    provider_name = "anthropic"
    capabilities = ProviderCapabilities(
        supports_system_prompt=True,
        supports_tool_calls=True,
        supports_json_schema=False,
        supports_streaming=True,
        supports_token_usage=True,
        supports_reasoning_summary=False,
        supports_local_hidden_state_access=False,
    )

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for Anthropic mode")
        self.api_key = api_key
        self.model = model

    async def generate(self, request: ModelRequest) -> ModelResponse:
        started = time.perf_counter()
        payload = {
            "model": self.model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "system": request.system,
            "messages": [{"role": "user", "content": request.prompt}],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages", headers=headers, json=payload
            )
            response.raise_for_status()
            data = response.json()
        text = "\n".join(
            block["text"] for block in data.get("content", []) if block.get("type") == "text"
        )
        return ModelResponse(
            text=text,
            provider=self.provider_name,
            model=data.get("model", self.model),
            usage=data.get("usage", {}),
            latency_ms=(time.perf_counter() - started) * 1000,
            metadata={"stop_reason": data.get("stop_reason"), "response_id": data.get("id")},
        )

    async def health_check(self) -> dict[str, object]:
        return {
            "healthy": True,
            "provider": self.provider_name,
            "model": self.model,
            "configured": True,
        }
