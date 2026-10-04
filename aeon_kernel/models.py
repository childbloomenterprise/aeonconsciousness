from __future__ import annotations

from dataclasses import asdict, dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from codebee_improve.storage import iso_now


def _clean_text(value: str, field_name: str) -> str:
    cleaned = str(value).strip()
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty.")
    if len(cleaned) > 2000:
        raise ValueError(f"{field_name} is too long.")
    return cleaned


@dataclass(frozen=True, slots=True)
class AgentIdentity:
    """Model-independent identity whose ownership and purpose cannot drift silently."""

    agent_id: str
    owner: str
    purpose: str
    created_at: str = field(default_factory=iso_now)
    schema_version: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "agent_id", _clean_text(self.agent_id, "agent_id"))
        object.__setattr__(self, "owner", _clean_text(self.owner, "owner"))
        object.__setattr__(self, "purpose", _clean_text(self.purpose, "purpose"))
        if self.schema_version != 1:
            raise ValueError("Unsupported AgentIdentity schema version.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "AgentIdentity":
        return cls(**value)


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    allowed: bool
    reason: str


@dataclass(frozen=True, slots=True)
class GoalContract:
    """Objective and externally delegated action envelope for one runtime."""

    objective: str
    success_metrics: tuple[str, ...] = ()
    hard_constraints: tuple[str, ...] = ()
    flexible_preferences: tuple[str, ...] = ()
    authorized_actions: frozenset[str] = frozenset()
    prohibited_actions: frozenset[str] = frozenset()
    resource_limits: Mapping[str, float] = field(default_factory=dict)
    approval_triggers: tuple[str, ...] = ()
    stop_conditions: tuple[str, ...] = ()
    deadline: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "objective", _clean_text(self.objective, "objective"))
        authorized = frozenset(str(item).strip() for item in self.authorized_actions if str(item).strip())
        prohibited = frozenset(str(item).strip() for item in self.prohibited_actions if str(item).strip())
        overlap = authorized & prohibited
        if overlap:
            raise ValueError(f"Actions cannot be both authorized and prohibited: {sorted(overlap)}")
        object.__setattr__(self, "authorized_actions", authorized)
        object.__setattr__(self, "prohibited_actions", prohibited)
        resource_limits = {str(name).strip(): float(amount) for name, amount in self.resource_limits.items()}
        for name, amount in resource_limits.items():
            if not str(name).strip() or float(amount) < 0:
                raise ValueError("Resource limits require a name and non-negative value.")
        object.__setattr__(self, "resource_limits", MappingProxyType(resource_limits))

    def authorize(self, action: str) -> AuthorizationDecision:
        action = str(action).strip()
        if action in self.prohibited_actions:
            return AuthorizationDecision(False, f"Action '{action}' is explicitly prohibited.")
        if self.authorized_actions and action not in self.authorized_actions:
            return AuthorizationDecision(False, f"Action '{action}' is outside the delegated authority envelope.")
        return AuthorizationDecision(True, "allowed")

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective": self.objective,
            "success_metrics": list(self.success_metrics),
            "hard_constraints": list(self.hard_constraints),
            "flexible_preferences": list(self.flexible_preferences),
            "authorized_actions": sorted(self.authorized_actions),
            "prohibited_actions": sorted(self.prohibited_actions),
            "resource_limits": dict(self.resource_limits),
            "approval_triggers": list(self.approval_triggers),
            "stop_conditions": list(self.stop_conditions),
            "deadline": self.deadline,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "GoalContract":
        return cls(
            objective=str(value["objective"]),
            success_metrics=tuple(str(item) for item in value.get("success_metrics", ())),
            hard_constraints=tuple(str(item) for item in value.get("hard_constraints", ())),
            flexible_preferences=tuple(str(item) for item in value.get("flexible_preferences", ())),
            authorized_actions=frozenset(str(item) for item in value.get("authorized_actions", ())),
            prohibited_actions=frozenset(str(item) for item in value.get("prohibited_actions", ())),
            resource_limits={str(key): float(amount) for key, amount in value.get("resource_limits", {}).items()},
            approval_triggers=tuple(str(item) for item in value.get("approval_triggers", ())),
            stop_conditions=tuple(str(item) for item in value.get("stop_conditions", ())),
            deadline=str(value["deadline"]) if value.get("deadline") else None,
        )
