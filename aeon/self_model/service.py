from __future__ import annotations

from datetime import UTC, datetime

from aeon.core.contracts import SelfModel
from aeon.storage.base import Storage


class SelfModelService:
    def __init__(self, storage: Storage, provider: str) -> None:
        self.storage = storage
        self.model = storage.load_self_model() or SelfModel()
        self.model.restart_history.append(datetime.now(UTC))
        self.model.boundaries.update(
            {
                "runtime": "AEON Alpha",
                "owned_storage": str(getattr(storage, "root", "abstract")),
                "attached_provider": provider,
                "provider_is_self": False,
            }
        )
        self.model.capabilities.update(
            {
                "persistent_identity": {"available": True, "validated": False},
                "private_hidden_state_access": {"available": False, "validated": True},
            }
        )
        self.model.internal_state.update(
            {
                "memory_integrity": "unchecked",
                "observer_health": "starting",
                "security_status": "research_mode",
            }
        )
        storage.save_self_model(self.model)

    def focus(self, text: str) -> SelfModel:
        self.model.current_focus = text[:160]
        self.storage.save_self_model(self.model)
        return self.model

    def migrate_provider(self, provider: str) -> SelfModel:
        previous = self.model.boundaries.get("attached_provider")
        if previous != provider:
            self.model.model_migration_history.append(
                {"from": previous, "to": provider, "at": datetime.now(UTC).isoformat()}
            )
            self.model.boundaries["attached_provider"] = provider
            self.storage.save_self_model(self.model)
        return self.model
