"""Provider-neutral integration API. Callbacks decide; AEON executes tools."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from aeon_world.gateway import ProviderError

from .models import ActionGrant, TaskSpec
from .providers import ModelReply, StructuredProvider
from .runner import TaskRunner, TaskStore


@dataclass(frozen=True, slots=True)
class AgentRequest:
    system: str
    payload: dict[str, Any]
    max_output_tokens: int
    image_paths: tuple[str, ...] = ()


class CallbackAdapter:
    """Wrap a synchronous model/agent callback with usage and error validation.

    The callback must honor max_output_tokens, report actual billed usage and
    configure its own network timeout. It must return decisions without running
    tools. Arbitrary Python callbacks are trusted operator code, not sandboxed.
    """

    def __init__(self, callback: Callable[[AgentRequest], ModelReply], *, supports_images: bool = False) -> None:
        if not callable(callback):
            raise TypeError("callback must be callable")
        self.callback = callback
        self.supports_images = supports_images

    def complete(self, system: str, payload: dict[str, Any], *, max_output_tokens: int = 8192) -> ModelReply:
        return self._complete(AgentRequest(system, payload, max_output_tokens))

    def complete_images(self, system: str, payload: dict[str, Any], image_paths: list[str], *, max_output_tokens: int = 2048) -> ModelReply:
        if not self.supports_images:
            raise ProviderError("This agent adapter does not support image input.")
        return self._complete(AgentRequest(system, payload, max_output_tokens, tuple(image_paths)))

    def _complete(self, request: AgentRequest) -> ModelReply:
        try:
            reply = self.callback(request)
        except KeyboardInterrupt:
            raise
        except Exception as error:
            # Provider/SDK exception messages may contain credentials or URLs.
            raise ProviderError(f"Agent callback failed ({type(error).__name__}); checkpoint can resume.") from error
        if not isinstance(reply, ModelReply) or not isinstance(reply.data, dict) or not reply.provider or not reply.model:
            raise ProviderError("Agent callback must return ModelReply with object data and a provider/model route.")
        if any(type(value) is not int or value < 0 for value in (reply.tokens, reply.input_tokens, reply.output_tokens)) or reply.tokens < reply.input_tokens + reply.output_tokens:
            raise ProviderError("Agent callback returned invalid token usage.")
        if reply.tokens == 0:
            raise ProviderError("Agent callback must report nonzero token usage, including retries.")
        return reply


def load_adapter(reference: str) -> StructuredProvider:
    """Load an operator-supplied module:factory (never retrieved page content)."""
    module, separator, factory = reference.partition(":")
    if not separator or not module or not factory.isidentifier():
        raise ValueError("Adapter must be module:factory, e.g. aeon_worker.demo:create_adapter")
    try:
        adapter = getattr(importlib.import_module(module), factory)()
    except Exception as error:
        raise ValueError(f"Cannot load adapter ({type(error).__name__}). Install its module in this environment.") from error
    if not callable(getattr(adapter, "complete", None)):
        raise ValueError("Adapter factory must return a structured provider with complete().")
    return adapter


class AEONWorker:
    """Embed the complete worker loop in an existing Python application."""

    def __init__(self, *, adapter: StructuredProvider | None = None, task_root: str | Path | None = None) -> None:
        self.store = TaskStore(Path(task_root) if task_root is not None else None)
        self.runner = TaskRunner(self.store, adapter)

    def run(self, brief: str, workspace: str | Path, *, grant: ActionGrant | None = None,
            deadline_minutes: int = 90, max_model_tokens: int = 50_000,
            max_steps: int = 32, max_revisions: int = 3) -> dict[str, Any]:
        result = self.runner.start(TaskSpec(brief, str(workspace), grant=grant or ActionGrant(),
                                         deadline_minutes=deadline_minutes, max_model_tokens=max_model_tokens,
                                         max_steps=max_steps, max_revisions=max_revisions))
        return self.store.result(result["task_id"])

    def resume(self, task_id: str, **extensions: int) -> dict[str, Any]:
        return self.runner.resume(task_id, **extensions)

    def status(self, task_id: str) -> dict[str, Any]:
        state = self.store.load(task_id)
        return {key: state[key] for key in ("task_id", "status", "phase", "steps", "tokens", "deadline_at")}

    def result(self, task_id: str) -> dict[str, Any]:
        return self.store.result(task_id)
