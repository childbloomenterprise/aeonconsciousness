from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field


class ProviderCapabilities(BaseModel):
    supports_system_prompt: bool = True
    supports_tool_calls: bool = False
    supports_json_schema: bool = False
    supports_streaming: bool = False
    supports_token_usage: bool = True
    supports_logprobs: bool = False
    supports_reasoning_summary: bool = False
    supports_embeddings: bool = False
    supports_local_hidden_state_access: bool = False


class ModelRequest(BaseModel):
    system: str
    prompt: str
    structured_state: dict[str, Any] = Field(default_factory=dict)
    temperature: float = 0.2
    max_tokens: int = 1200


class ModelResponse(BaseModel):
    text: str
    provider: str
    model: str
    usage: dict[str, int] = Field(default_factory=dict)
    latency_ms: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModelProvider(Protocol):
    provider_name: str
    capabilities: ProviderCapabilities

    async def generate(self, request: ModelRequest) -> ModelResponse: ...
    async def health_check(self) -> dict[str, Any]: ...
