from __future__ import annotations

import time

import httpx

from aeon.providers.base import ModelRequest, ModelResponse, ProviderCapabilities


class GeminiProvider:
    provider_name = "gemini"
    capabilities = ProviderCapabilities(
        supports_system_prompt=True,
        supports_tool_calls=True,
        supports_json_schema=True,
        supports_streaming=True,
        supports_token_usage=True,
        supports_reasoning_summary=False,
        supports_local_hidden_state_access=False,
    )

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is required for Gemini mode")
        self.api_key, self.model = api_key, model

    async def generate(self, request: ModelRequest) -> ModelResponse:
        started = time.perf_counter()
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        )
        payload = {
            "systemInstruction": {"parts": [{"text": request.system}]},
            "contents": [{"role": "user", "parts": [{"text": request.prompt}]}],
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
            },
        }
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                url,
                headers={"x-goog-api-key": self.api_key, "content-type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        candidate = data.get("candidates", [{}])[0]
        parts = candidate.get("content", {}).get("parts", [])
        text = "\n".join(part.get("text", "") for part in parts if part.get("text"))
        usage = data.get("usageMetadata", {})
        return ModelResponse(
            text=text,
            provider=self.provider_name,
            model=self.model,
            usage={
                "input_tokens": usage.get("promptTokenCount", 0),
                "output_tokens": usage.get("candidatesTokenCount", 0),
                "total_tokens": usage.get("totalTokenCount", 0),
            },
            latency_ms=(time.perf_counter() - started) * 1000,
            metadata={
                "finish_reason": candidate.get("finishReason"),
                "response_id": data.get("responseId"),
            },
        )

    async def health_check(self) -> dict[str, object]:
        return {"healthy": True, "provider": self.provider_name, "model": self.model}
