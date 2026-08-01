from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from aeon.ahamkara import Ahamkara
from aeon.buddhi import Buddhi
from aeon.citta import Citta
from aeon.config import Settings, get_settings
from aeon.control_plane import ControlPlane
from aeon.core.attention import Attention
from aeon.core.contracts import CognitiveEvent, ControlSignal, CycleResult, new_id
from aeon.core.workspace import GlobalWorkspace
from aeon.experiments import ExperimentEngine
from aeon.manas import Manas
from aeon.metacognition import MetacognitiveController, MetacognitiveMonitor
from aeon.model_observer import ModelBehaviourObserver
from aeon.providers import (
    AnthropicProvider,
    GeminiProvider,
    MockProvider,
    OpenAICompatibleProvider,
)
from aeon.providers.base import ModelProvider, ModelRequest
from aeon.sakshin import SakshinObserver
from aeon.self_model import SelfModelService
from aeon.storage.local import LocalStorage
from aeon.storage.supabase import SupabaseMirror
from aeon.vi_mode import VIMode
from aeon.world_model import WorldModel


SYSTEM_PROMPT = """You are the replaceable reasoning organ inside AEON Research Core Alpha.
Return a concise evidence-grounded synthesis. Distinguish observation, retrieved memory, inference,
hypothesis, and unknown. Do not claim access to hidden provider reasoning or prove consciousness.
Private chain-of-thought is neither requested nor exposed; provide only structured conclusions."""


class AeonRuntime:
    def __init__(
        self,
        settings: Settings | None = None,
        provider: ModelProvider | None = None,
        runtime_dir: Path | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.storage = LocalStorage(
            runtime_dir or self.settings.aeon_runtime_dir, self.settings.aeon_observer_signing_key
        )
        self.provider = provider or self._provider()
        self.cloud = self._cloud_mirror()
        self._cloud_tasks: list[asyncio.Task[None]] = []
        self._cloud_errors: list[str] = []
        self.control = ControlPlane()
        self.manas = Manas(self.settings.aeon_mock_seed)
        self.attention = Attention()
        self.workspace = GlobalWorkspace(self.settings.aeon_workspace_capacity)
        self.citta = Citta(self.storage)
        self.self_model = SelfModelService(self.storage, self.provider.provider_name)
        self.world_model = WorldModel()
        self.monitor = MetacognitiveMonitor()
        self.controller = MetacognitiveController()
        self.buddhi = Buddhi()
        self.ahamkara = Ahamkara()
        self.model_observer = ModelBehaviourObserver(self.storage)
        self.sakshin = SakshinObserver(self.storage)
        self.vi_mode = VIMode(self.storage)
        self.experiments = ExperimentEngine(self.storage)
        self._subscribers: list[asyncio.Queue[dict[str, Any]]] = []

    def _provider(self) -> ModelProvider:
        provider = self.settings.aeon_model_provider.lower()
        if provider == "anthropic":
            return AnthropicProvider(
                self.settings.anthropic_api_key or "", self.settings.aeon_model_name
            )
        if provider == "gemini":
            return GeminiProvider(self.settings.google_api_key or "", self.settings.aeon_model_name)
        if provider == "openai_compatible":
            if not self.settings.openai_compatible_base_url:
                raise ValueError("OPENAI_COMPATIBLE_BASE_URL is required")
            return OpenAICompatibleProvider(
                self.settings.openai_compatible_base_url,
                self.settings.openai_compatible_api_key or "",
                self.settings.aeon_model_name,
            )
        if provider == "mock":
            return MockProvider(self.settings.aeon_mock_seed)
        raise ValueError(f"Unknown AEON_MODEL_PROVIDER: {provider}")

    def _cloud_mirror(self) -> SupabaseMirror | None:
        mode = self.settings.aeon_runtime_mode.lower()
        if mode not in {"cloud", "hybrid"}:
            return None
        if not self.settings.supabase_url or not self.settings.supabase_service_role_key:
            raise ValueError(
                "Cloud/hybrid mode requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY"
            )
        return SupabaseMirror(self.settings.supabase_url, self.settings.supabase_service_role_key)

    def _mirror_event(self, event: CognitiveEvent) -> None:
        if not self.cloud:
            return
        record = event.model_dump(mode="json")
        payload = {
            key: record[key]
            for key in (
                "event_id",
                "cycle_id",
                "timestamp",
                "actor",
                "event_type",
                "payload",
                "previous_event_hash",
                "event_hash",
                "signature",
            )
        }
        task = asyncio.create_task(self.cloud.append("aeon_events", payload))
        self._cloud_tasks.append(task)

    async def _drain_cloud(self) -> None:
        pending, self._cloud_tasks = self._cloud_tasks, []
        if not pending:
            return
        results = await asyncio.gather(*pending, return_exceptions=True)
        self._cloud_errors.extend(
            str(result) for result in results if isinstance(result, Exception)
        )

    def _event(
        self,
        cycle_id: str,
        actor: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
        **refs: Any,
    ) -> CognitiveEvent:
        event = self.storage.append_event(
            CognitiveEvent(
                cycle_id=cycle_id, actor=actor, event_type=event_type, payload=payload or {}, **refs
            )
        )
        self._mirror_event(event)
        message = event.model_dump(mode="json")
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                pass
        return event

    async def process(self, text: str) -> CycleResult:
        if self.control.state.paused:
            raise RuntimeError("AEON runtime is paused")
        cycle_id = new_id("cycle")
        self._event(cycle_id, "external", "input_received", {"text": text})
        self.self_model.focus(text)
        self._event(
            cycle_id, "self_model", "focus_updated", {"focus": self.self_model.model.current_focus}
        )
        world_state = self.world_model.interpret(text)
        self._event(cycle_id, "world_model", "world_state_updated", world_state)

        retrieved = self.citta.retrieve(text)
        memories = [memory for memory, _ in retrieved]
        self._event(
            cycle_id,
            "citta",
            "memory_retrieved",
            {"scores": {memory.memory_id: score for memory, score in retrieved}},
            memory_refs=[memory.memory_id for memory in memories],
        )

        iterations = 0
        candidates = []
        workspace = []
        report = self.monitor.assess(text, [], len(memories), 1)
        previous_ids: tuple[str, ...] = ()
        while iterations < self.settings.aeon_max_cycles:
            iterations += 1
            candidates = self.manas.generate(cycle_id, text, [m.memory_id for m in memories])
            self._event(
                cycle_id,
                "manas",
                "candidates_generated",
                {"iteration": iterations, "count": len(candidates)},
                output_refs=[c.candidate_id for c in candidates],
            )
            winners, rejected = self.attention.compete(candidates, self.workspace.capacity)
            workspace = self.workspace.broadcast(winners)
            self._event(
                cycle_id,
                "attention",
                "salience_competition",
                {
                    "iteration": iterations,
                    "winners": [c.model_dump(mode="json") for c in winners],
                    "rejected": [
                        {"candidate_id": c.candidate_id, "salience": c.salience} for c in rejected
                    ],
                },
                output_refs=[c.candidate_id for c in winners],
            )
            self._event(
                cycle_id,
                "workspace",
                "workspace_broadcast",
                self.workspace.snapshot(),
                workspace_state_ref=f"{cycle_id}:{iterations}",
            )
            report = self.monitor.assess(text, workspace, len(memories), iterations)
            intervention = self.controller.intervene(report)
            self._event(
                cycle_id,
                "metacognition",
                "monitor_and_control",
                {"report": report.model_dump(mode="json"), "intervention": intervention},
                confidence=report.confidence,
            )
            current_ids = tuple(c.content for c in workspace)
            if (
                current_ids == previous_ids
                or report.control_signal == ControlSignal.CONTINUE
                and iterations >= 2
            ):
                break
            previous_ids = current_ids

        evidence = [m.memory_id for m in memories]
        request = ModelRequest(
            system=SYSTEM_PROMPT,
            prompt=text,
            structured_state={
                "focus": self.self_model.model.current_focus,
                "workspace": [c.model_dump(mode="json") for c in workspace],
                "evidence": evidence,
                "metacognition": report.model_dump(mode="json"),
                "world_state": world_state,
            },
        )
        response = await self.provider.generate(request)
        model_trace = self.model_observer.record(cycle_id, request, response)
        self._event(
            cycle_id,
            "model_observer",
            "provider_interaction_recorded",
            {
                "trace_id": model_trace["trace_id"],
                "provider": response.provider,
                "model": response.model,
                "usage": response.usage,
            },
        )
        belief, approved = self.buddhi.evaluate(response.text, evidence, report, response.provider)
        self._event(
            cycle_id,
            "buddhi",
            "epistemic_gate",
            {"approved": approved, "belief": belief.model_dump(mode="json")},
            belief_refs=[belief.belief_id],
            confidence=belief.confidence,
        )
        if approved:
            self.storage.write_record("beliefs", belief.model_dump(mode="json"))
        ownership = self.ahamkara.bind(
            self.self_model.model.continuity_id,
            response.provider,
            evidence,
            response.metadata.get("response_id"),
        )
        self._event(cycle_id, "ahamkara", "ownership_bound", ownership)
        result = CycleResult(
            cycle_id=cycle_id,
            input_text=text,
            response=response.text,
            candidates=candidates,
            workspace=workspace,
            memories=memories,
            metacognition=report,
            belief_proposal=belief,
            ownership=ownership,
            provider_metadata={
                "provider": response.provider,
                "model": response.model,
                "usage": response.usage,
                "latency_ms": response.latency_ms,
            },
            iterations=iterations,
        )
        self.storage.write_record("cycles", result.model_dump(mode="json"))
        remembered = self.citta.remember(
            f"Input: {text}\nAEON: {response.text}",
            "episodic",
            "cognitive_cycle",
            [cycle_id],
            report.confidence,
        )
        self._event(
            cycle_id,
            "citta",
            "memory_created",
            {"memory_type": remembered.memory_type},
            memory_refs=[remembered.memory_id],
        )
        witness = self.sakshin.witness(cycle_id, {"memory_refs": evidence})
        self._event(
            cycle_id,
            "sakshin",
            "witness_report_created",
            {"status": witness["status"], "report_id": witness["report_id"]},
        )
        await self._drain_cloud()
        return result

    def status(self) -> dict[str, Any]:
        events = self.storage.list_events()
        witness = self.storage.list_records("witness")
        return {
            "status": "paused" if self.control.state.paused else "running",
            "continuity_id": self.self_model.model.continuity_id,
            "provider": self.provider.provider_name,
            "model": getattr(self.provider, "model", "aeon-deterministic-mock-v1"),
            "mode": self.settings.aeon_runtime_mode,
            "cloud_mirror": {
                "enabled": self.cloud is not None,
                "pending": len(self._cloud_tasks),
                "errors": self._cloud_errors[-5:],
            },
            "current_focus": self.self_model.model.current_focus,
            "events": len(events),
            "memories": len(self.storage.list_memories()),
            "beliefs": len(self.storage.list_records("beliefs")),
            "observer_health": witness[-1]["status"] if witness else "INSUFFICIENT_TELEMETRY",
            "audit_integrity": self.storage.verify_event_chain(),
            "phenomenal_consciousness": "UNKNOWN",
        }

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=500)
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        if queue in self._subscribers:
            self._subscribers.remove(queue)
