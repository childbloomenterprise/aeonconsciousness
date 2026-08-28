from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .backends import Ai2ThorBackend, DeterministicBackend, HazardBackend, WorldBackend
from .gateway import ModelClient, client_for
from .ledger import EventLedger, default_runtime_root
from .models import ActionProposal, EntityConfig
from .policy import ActionPolicy


class WorldRunner:
    def __init__(
        self,
        config: dict[str, Any],
        *,
        backend: WorldBackend | None = None,
        clients: dict[str, ModelClient] | None = None,
        run_dir: Path | None = None,
    ):
        self.config = config
        run_config = config.get("run", {})
        self.run_id = str(run_config.get("run_id") or f"aeon-{uuid.uuid4().hex[:10]}")
        self.entities = tuple(EntityConfig.from_dict(value) for value in config.get("entities", []))
        if not self.entities:
            raise ValueError("Configuration requires at least one entity.")
        self.max_ticks = int(run_config.get("ticks", 100))
        self.duration_seconds = float(run_config.get("duration_seconds", 0.0))
        self.interval_seconds = float(run_config.get("tick_interval_seconds", 0.0))
        self.interventions = tuple(config.get("interventions", ()))
        self.backend = backend or self._create_backend(run_config)
        self.clients = clients or {entity.entity_id: client_for(entity) for entity in self.entities}
        allowed = config.get("policy", {}).get("allowed_actions")
        self.policy = ActionPolicy(set(allowed) if allowed else None)
        root = run_dir or default_runtime_root() / self.run_id
        self.ledger = EventLedger(root)
        self.memories: dict[str, list[str]] = {entity.entity_id: [] for entity in self.entities}
        self.token_usage: dict[str, int] = {entity.entity_id: 0 for entity in self.entities}

    @staticmethod
    def _create_backend(run_config: dict[str, Any]) -> WorldBackend:
        backend_name = str(run_config.get("backend", "fake"))
        scene = str(run_config.get("scene", "FloorPlan1"))
        if backend_name == "fake":
            return DeterministicBackend(scene=scene)
        if backend_name == "ai2thor":
            return Ai2ThorBackend(
                scene=scene,
                width=int(run_config.get("width", 640)),
                height=int(run_config.get("height", 480)),
                quality=str(run_config.get("quality", "Low")),
                cloud_rendering=bool(run_config.get("cloud_rendering", False)),
            )
        if backend_name == "hazard":
            return HazardBackend(scenario=str(run_config.get("scenario", "rising_water")))
        raise ValueError(f"Unknown backend '{backend_name}'.")

    def _remember(self, entity: EntityConfig, proposal: ActionProposal, result: dict[str, Any]) -> None:
        outcome = f"VERIFIED {proposal.action}: {'succeeded' if result['success'] else 'failed'}"
        if result.get("error_message"):
            outcome += f" ({result['error_message']})"
        inventory = result.get("inventory", ())
        inventory_types = [str(item.get("object_type", item.get("object_id", "unknown"))) for item in inventory]
        outcome += f"; inventory={inventory_types}"
        claimed_note = proposal.memory_note.strip()
        note = f"{outcome}; prior model note={claimed_note}" if claimed_note else outcome
        memories = self.memories[entity.entity_id]
        memories.append(note[:500])
        del memories[:-entity.memory_limit]

    def run(self) -> dict[str, Any]:
        self.ledger.start_run(self.run_id, self.config)
        self.ledger.write_control("run")
        tick = 0
        status = "running"
        backend_started = False
        try:
            self.backend.start(len(self.entities))
            backend_started = True
            self.ledger.append(
                self.run_id,
                tick,
                "world_started",
                {"entities": [asdict(entity) | {"api_key_env": entity.api_key_env} for entity in self.entities], "world": self.backend.snapshot()},
            )
            run_started_at = time.monotonic()
            while self.max_ticks <= 0 or tick < self.max_ticks:
                if self.duration_seconds > 0 and time.monotonic() - run_started_at >= self.duration_seconds:
                    status = "completed"
                    break
                tick += 1
                command = self.ledger.read_control()
                while command == "pause":
                    status = "paused"
                    self.ledger.update_run(self.run_id, tick=tick - 1, status=status)
                    time.sleep(1.0)
                    command = self.ledger.read_control()
                if command == "stop":
                    status = "stopped"
                    break
                status = "running"

                for intervention in self.interventions:
                    if int(intervention.get("tick", -1)) != tick:
                        continue
                    agent_index = int(intervention.get("agent_index", 0))
                    if not 0 <= agent_index < len(self.entities):
                        raise ValueError(f"Intervention agent_index {agent_index} is out of range.")
                    entity = self.entities[agent_index]
                    before = self.backend.observe(entity.entity_id, agent_index, tick)
                    proposal = ActionProposal.from_dict(dict(intervention.get("proposal", {})))
                    policy = self.policy.validate(proposal, before)
                    if not policy.allowed or policy.action is None:
                        raise ValueError(f"Invalid intervention: {policy.reason}")
                    result = self.backend.act(agent_index, policy.action)
                    self.ledger.append(
                        self.run_id,
                        tick,
                        "experimenter_intervention",
                        {
                            "label": str(intervention.get("label", "controlled intervention")),
                            "proposal": proposal.to_dict(),
                            "result": result.to_dict(),
                        },
                        entity_id=entity.entity_id,
                    )

                for agent_index, entity in enumerate(self.entities):
                    observation = self.backend.observe(entity.entity_id, agent_index, tick)
                    self.ledger.append(
                        self.run_id,
                        tick,
                        "observation",
                        observation.to_dict(),
                        entity_id=entity.entity_id,
                    )
                    try:
                        client = self.clients[entity.entity_id]
                        started = time.perf_counter()
                        if self.token_usage[entity.entity_id] >= entity.token_budget:
                            proposal = ActionProposal(
                                "Done",
                                prediction="Token budget exhausted.",
                                confidence=1.0,
                                decision_summary="External budget controller stopped model calls.",
                            )
                            usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
                            self.ledger.append(
                                self.run_id,
                                tick,
                                "budget_exhausted",
                                {"token_budget": entity.token_budget, "tokens_used": self.token_usage[entity.entity_id]},
                                entity_id=entity.entity_id,
                            )
                        else:
                            proposal = client.decide(
                                entity,
                                observation,
                                tuple(self.memories[entity.entity_id]),
                            )
                            usage = dict(getattr(client, "last_usage", {}) or {})
                            self.token_usage[entity.entity_id] += int(usage.get("total_tokens", 0))
                        latency_ms = round((time.perf_counter() - started) * 1000, 2)
                        self.ledger.append(
                            self.run_id,
                            tick,
                            "decision",
                            {
                                **proposal.to_dict(),
                                "model": entity.model,
                                "provider": entity.provider,
                                "credential_alias": entity.api_key_env,
                                "latency_ms": latency_ms,
                                "usage": usage,
                                "tokens_used": self.token_usage[entity.entity_id],
                                "token_budget": entity.token_budget,
                            },
                            entity_id=entity.entity_id,
                        )
                    except Exception as error:
                        self.ledger.append(
                            self.run_id,
                            tick,
                            "model_error",
                            {"error": str(error), "model": entity.model, "provider": entity.provider},
                            entity_id=entity.entity_id,
                        )
                        proposal = ActionProposal("Done", prediction="Provider unavailable.", confidence=0.0)

                    policy = self.policy.validate(proposal, observation)
                    if not policy.allowed or policy.action is None:
                        self.ledger.append(
                            self.run_id,
                            tick,
                            "action_denied",
                            {"proposal": proposal.to_dict(), "reason": policy.reason},
                            entity_id=entity.entity_id,
                        )
                        continue

                    result = self.backend.act(agent_index, policy.action)
                    result_payload = result.to_dict()
                    self.ledger.append(
                        self.run_id,
                        tick,
                        "action_result",
                        {"proposal": proposal.to_dict(), "policy_reason": policy.reason, **result_payload},
                        entity_id=entity.entity_id,
                    )
                    self._remember(entity, proposal, result_payload)
                    frame = self.backend.frame_jpeg(agent_index)
                    if frame:
                        self.ledger.write_frame(entity.entity_id, frame)

                self.ledger.append(
                    self.run_id,
                    tick,
                    "heartbeat",
                    {
                        "world": self.backend.snapshot(),
                        "memory_counts": {key: len(value) for key, value in self.memories.items()},
                        "token_usage": dict(self.token_usage),
                    },
                )
                self.ledger.update_run(self.run_id, tick=tick, status=status)
                if self.interval_seconds > 0:
                    time.sleep(self.interval_seconds)
            if status == "running" and self.max_ticks > 0 and tick >= self.max_ticks:
                status = "completed"
        except KeyboardInterrupt:
            status = "interrupted"
        except Exception as error:
            status = "failed"
            self.ledger.append(self.run_id, tick, "world_error", {"error": str(error)})
            raise
        finally:
            if backend_started:
                self.backend.close()
            self.ledger.update_run(self.run_id, tick=tick, status=status)
            self.ledger.append(
                self.run_id,
                tick,
                "world_stopped",
                {"status": status, "audit_valid": self.ledger.verify(self.run_id)},
            )
        return {
            "run_id": self.run_id,
            "run_dir": str(self.ledger.run_dir),
            "status": status,
            "tick": tick,
            "audit_valid": self.ledger.verify(self.run_id),
        }


def load_config(path: Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("Configuration root must be an object.")
    return value
