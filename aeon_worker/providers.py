"""Provider-neutral structured completions with a visible NVIDIA -> Gemini route."""

from __future__ import annotations

import json
import base64
import os
import random
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Protocol

from aeon_world.gateway import NvidiaStructuredClient, ProviderError
from .models import TOOL_NAMES


class StructuredContentError(ProviderError):
    """Provider replied, but did not supply usable structured model content."""


@dataclass(frozen=True, slots=True)
class ModelReply:
    data: dict[str, Any]
    provider: str
    model: str
    tokens: int
    input_tokens: int = 0
    output_tokens: int = 0
    fallback_from: str | None = None
    fallback_reason: str | None = None
    route_events: tuple[dict[str, str], ...] = ()


class StructuredProvider(Protocol):
    def complete(self, system: str, payload: dict[str, Any], *, max_output_tokens: int = 16_384) -> ModelReply: ...


def _json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.S)
    if fenced:
        stripped = fenced.group(1)
    elif not stripped.startswith("{"):
        start, end = stripped.find("{"), stripped.rfind("}")
        stripped = stripped[start : end + 1] if start >= 0 and end > start else stripped
    value = json.loads(stripped)
    if not isinstance(value, dict):
        raise ValueError("Provider response was not a JSON object.")
    return value


class ProviderRouter:
    def __init__(
        self,
        *,
        nvidia_model: str = "meta/llama-3.1-70b-instruct",
        gemini_model: str = "gemini-3.5-flash-lite",
        gemini_backup_model: str | None = "gemini-3.1-flash-lite",
        nvidia_client: NvidiaStructuredClient | None = None,
        forced_provider: str | None = None,
    ):
        if forced_provider not in {None, "nvidia", "gemini"}:
            raise ValueError("forced_provider must be nvidia or gemini.")
        self.nvidia_model = nvidia_model
        self.gemini_model = gemini_model
        self.gemini_backup_model = gemini_backup_model if gemini_backup_model != gemini_model else None
        self._prefer_gemini_backup = False
        self.nvidia_client = nvidia_client or NvidiaStructuredClient()
        self.forced_provider = forced_provider
        self.usage_events: list[dict[str, Any]] = []
        self._codex = None
        if forced_provider is None and os.environ.get("AEON_MODEL_BACKEND") == "codex":
            from .codex_provider import CodexStructuredClient
            self._codex = CodexStructuredClient()

    def complete(self, system: str, payload: dict[str, Any], *, max_output_tokens: int = 16_384) -> ModelReply:
        self.usage_events = []
        if self._codex is not None:
            try:
                return self._codex.complete(system, payload, max_output_tokens=max_output_tokens)
            finally:
                self.usage_events = self._codex.usage_events
        if self.forced_provider == "gemini":
            if not os.environ.get("GEMINI_API_KEY"):
                raise ProviderError("GEMINI_API_KEY is required for the fixed Gemini route.")
            return self._gemini_routed(system, payload, max_output_tokens=max_output_tokens)
        nvidia_error: Exception | None = None
        if os.environ.get("NVIDIA_API_KEY"):
            try:
                response = self.nvidia_client.complete(
                    model=self.nvidia_model,
                    api_key_env="NVIDIA_API_KEY",
                    rpm_limit=30,
                    system=system,
                    user_payload=payload,
                    temperature=0.3,
                    top_p=0.9,
                    max_tokens=max_output_tokens,
                )
                self.usage_events.append({"provider": "nvidia", "model": self.nvidia_model, "tokens": int(response.usage.get("total_tokens", 0)), "input_tokens": int(response.usage.get("prompt_tokens", 0)), "output_tokens": int(response.usage.get("completion_tokens", 0))})
                return ModelReply(
                    _json_object(response.content), "nvidia", self.nvidia_model,
                    int(response.usage.get("total_tokens", 0)),
                    int(response.usage.get("prompt_tokens", 0)),
                    int(response.usage.get("completion_tokens", 0)),
                )
            except (ProviderError, ValueError, json.JSONDecodeError) as error:
                nvidia_error = error
        if self.forced_provider == "nvidia":
            raise ProviderError("Fixed NVIDIA route was unavailable.") from nvidia_error
        if not os.environ.get("GEMINI_API_KEY"):
            detail = f" NVIDIA failed: {type(nvidia_error).__name__}." if nvidia_error else ""
            raise ProviderError("Neither NVIDIA_API_KEY nor GEMINI_API_KEY is usable." + detail)
        reply = self._gemini_routed(system, payload, max_output_tokens=max_output_tokens)
        nvidia_event = {
            "from": "nvidia", "to": "gemini",
            "reason": type(nvidia_error).__name__ if nvidia_error else "nvidia_key_absent",
        }
        return replace(
            reply, fallback_from="nvidia",
            fallback_reason=nvidia_event["reason"],
            route_events=(nvidia_event, *reply.route_events),
        )

    def complete_images(self, system: str, payload: dict[str, Any], image_paths: list[str], *, max_output_tokens: int = 16_384) -> ModelReply:
        self.usage_events = []
        if self._codex is not None:
            try:
                return self._codex.complete_images(system, payload, image_paths, max_output_tokens=max_output_tokens)
            finally:
                self.usage_events = self._codex.usage_events
        if self.forced_provider == "nvidia" or not os.environ.get("GEMINI_API_KEY"):
            raise ProviderError("Gemini image review is unavailable on this route.")
        return self._gemini_routed(system, payload, image_paths=image_paths, max_output_tokens=max_output_tokens)

    def _gemini_routed(self, system: str, payload: dict[str, Any], *, image_paths: list[str] | None = None, max_output_tokens: int = 16_384) -> ModelReply:
        primary = self.gemini_backup_model if self._prefer_gemini_backup else self.gemini_model
        assert primary is not None
        try:
            return self._gemini(
                system, payload, image_paths=image_paths, max_output_tokens=max_output_tokens,
                model=primary, retry_rate_limit=not bool(self.gemini_backup_model and primary != self.gemini_backup_model),
            )
        except ProviderError as error:
            if not self.gemini_backup_model or primary == self.gemini_backup_model:
                raise
            reply = self._gemini(
                system, payload, image_paths=image_paths, max_output_tokens=max_output_tokens,
                model=self.gemini_backup_model,
            )
            self._prefer_gemini_backup = True
            fallback = {"from": f"gemini:{primary}", "to": f"gemini:{self.gemini_backup_model}", "reason": str(error)[:120]}
            return replace(reply, route_events=(*reply.route_events, fallback))

    def _gemini(self, system: str, payload: dict[str, Any], *, image_paths: list[str] | None = None, max_output_tokens: int = 16_384, model: str | None = None, retry_rate_limit: bool = True) -> ModelReply:
        key = os.environ["GEMINI_API_KEY"]
        model = model or self.gemini_model
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        parts: list[dict[str, Any]] = [{"text": json.dumps(payload, ensure_ascii=False)}]
        for path in (image_paths or [])[:2]:
            raw = Path(path).read_bytes()
            if len(raw) > 8_000_000:
                raise ValueError("Screenshot exceeds Gemini inline image limit for AEON.")
            parts.append({"inline_data": {"mime_type": "image/png", "data": base64.b64encode(raw).decode("ascii")}})
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": min(8192, max_output_tokens), "responseMimeType": "application/json"},
        }
        if "available_tools" in payload:
            body["generationConfig"]["responseJsonSchema"] = {
                "type": "object", "properties": {
                    "tool": {"type": "string", "enum": list(TOOL_NAMES)},
                    "args": {"type": "object", "additionalProperties": True},
                    "decision_summary": {"type": "string"},
                }, "required": ["tool", "args", "decision_summary"],
                "additionalProperties": True,
            }
        for attempt in range(3):
            try:
                if attempt:
                    body["generationConfig"]["maxOutputTokens"] = min(16_384, max_output_tokens)
                request = urllib.request.Request(
                    url,
                    data=json.dumps(body).encode("utf-8"),
                    headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=60) as response:
                    envelope = json.load(response)
                usage = envelope.get("usageMetadata", {})
                self.usage_events.append({"provider": "gemini", "model": model, "tokens": int(usage.get("totalTokenCount", 0)), "input_tokens": int(usage.get("promptTokenCount", 0)), "output_tokens": int(usage.get("candidatesTokenCount", 0)) + int(usage.get("thoughtsTokenCount", 0))})
                parts = envelope["candidates"][0]["content"]["parts"]
                content = "".join(part.get("text", "") for part in parts)
                return ModelReply(
                    _json_object(content), "gemini", model,
                    int(usage.get("totalTokenCount", 0)),
                    int(usage.get("promptTokenCount", 0)),
                    int(usage.get("candidatesTokenCount", 0)) + int(usage.get("thoughtsTokenCount", 0)),
                )
            except urllib.error.HTTPError as error:
                if error.code == 429 and not retry_rate_limit:
                    raise ProviderError("Gemini HTTP 429.") from error
                if error.code not in {429, 500, 502, 503, 504} or attempt == 2:
                    raise ProviderError(f"Gemini HTTP {error.code}.") from error
                if error.code == 429:
                    raw_retry = error.headers.get("Retry-After", "") if error.headers else ""
                    try:
                        retry_delay = float(raw_retry)
                    except ValueError:
                        retry_delay = 15.0 * (attempt + 1)
                    time.sleep(min(60.0, max(1.0, retry_delay)))
                else:
                    time.sleep(min(10, 2 ** attempt + random.random()))
            except (urllib.error.URLError, TimeoutError) as error:
                if attempt == 2:
                    raise ProviderError("Gemini unavailable.") from error
                time.sleep(2 ** attempt + random.random())
            except (KeyError, IndexError, ValueError, json.JSONDecodeError) as error:
                if attempt == 2:
                    raise StructuredContentError("Gemini returned invalid structured content after retries.") from error
                time.sleep(1)
        raise ProviderError("Gemini retry limit reached.")
