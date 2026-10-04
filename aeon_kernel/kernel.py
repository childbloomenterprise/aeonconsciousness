from __future__ import annotations

from pathlib import Path
from typing import Any

from codebee_improve import Candidate, SelfImprovementEngine
from codebee_improve.storage import atomic_write_json, file_lock, read_json

from .models import AgentIdentity, GoalContract


class IdentityConflictError(ValueError):
    """Raised when stored identity ownership or purpose would change silently."""


class AEONKernel:
    """Durable identity, goal authority, and approval-gated learning bridge."""

    def __init__(
        self,
        root: Path,
        *,
        identity: AgentIdentity,
        goal_contract: GoalContract,
        require_approval: bool = True,
    ):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.identity_path = self.root / "identity.json"
        self.identity_lock_path = self.root / "identity.lock"
        self.identity = self._load_or_create_identity(identity)
        self.goal_contract = goal_contract
        self.improvement = SelfImprovementEngine(
            self.root,
            require_approval=require_approval,
        )

    def _load_or_create_identity(self, requested: AgentIdentity) -> AgentIdentity:
        with file_lock(self.identity_lock_path):
            stored_value = read_json(self.identity_path, None)
            if stored_value is None:
                atomic_write_json(self.identity_path, requested.to_dict())
                return requested
            stored = AgentIdentity.from_dict(stored_value)
            immutable = ("agent_id", "owner", "purpose")
            changes = [name for name in immutable if getattr(stored, name) != getattr(requested, name)]
            if changes:
                raise IdentityConflictError(
                    "Stored identity conflicts with requested identity fields: " + ", ".join(changes)
                )
            return stored

    @staticmethod
    def memory_namespace(entity_id: str) -> str:
        normalized = "".join(character.lower() if character.isalnum() else "-" for character in entity_id).strip("-")
        if not normalized:
            raise ValueError("entity_id must contain an alphanumeric character.")
        return f"agent.{normalized[:57]}"

    def approved_memories(self, entity_id: str) -> tuple[str, ...]:
        namespace = self.memory_namespace(entity_id)
        return tuple(entry.content for entry in self.improvement.memory.list(namespace))

    def stage_verified_outcome(
        self,
        *,
        entity_id: str,
        event: dict[str, Any],
        proposal: Any,
        result: dict[str, Any],
    ) -> Candidate:
        event_id = str(event.get("event_id", "")).strip()
        event_hash = str(event.get("event_hash", "")).strip()
        if not event_id or not event_hash:
            raise ValueError("Verified outcome requires an event_id and event_hash.")
        status = "succeeded" if bool(result.get("success")) else "failed"
        # Raw environment text stays in the evidence ledger. It is intentionally
        # not copied into durable candidates where it could carry injected
        # instructions or sensitive values.
        content = f"VERIFIED {proposal.action} {status}; evidence_event={event_id}"
        return self.improvement.propose_memory(
            namespace=self.memory_namespace(entity_id),
            content=content,
            rationale="Retain an independently recorded runtime outcome for evaluation before reuse.",
            provenance=f"event:{event_id}|hash:{event_hash}",
            actor=self.identity.agent_id,
        )
