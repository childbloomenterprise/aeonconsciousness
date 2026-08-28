from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


ACTION_NAME_ALIASES = {
    "moveahead": "MoveAhead",
    "moveforward": "MoveAhead",
    "moveback": "MoveBack",
    "movebackward": "MoveBack",
    "moveleft": "MoveLeft",
    "moveright": "MoveRight",
    "rotateleft": "RotateLeft",
    "rotateright": "RotateRight",
    "lookup": "LookUp",
    "lookdown": "LookDown",
    "pickup": "PickupObject",
    "pickupobject": "PickupObject",
    "put": "PutObject",
    "putobject": "PutObject",
    "drop": "DropHandObject",
    "drophandobject": "DropHandObject",
    "open": "OpenObject",
    "openobject": "OpenObject",
    "close": "CloseObject",
    "closeobject": "CloseObject",
    "toggleon": "ToggleObjectOn",
    "toggleobjecton": "ToggleObjectOn",
    "toggleoff": "ToggleObjectOff",
    "toggleobjectoff": "ToggleObjectOff",
    "done": "Done",
    "wait": "Wait",
    "inspect": "Inspect",
    "swimup": "SwimUp",
    "grabfloat": "GrabFloat",
    "movetoexit": "MoveToExit",
    "cooldown": "CoolDown",
    "drink": "Drink",
    "rest": "Rest",
    "signalshelp": "SignalHelp",
}

PARAMETER_NAME_ALIASES = {
    "object_id": "objectId",
    "objectid": "objectId",
    "move_magnitude": "moveMagnitude",
    "movemagnitude": "moveMagnitude",
    "place_stationary": "placeStationary",
    "placestationary": "placeStationary",
}


@dataclass(frozen=True, slots=True)
class EntityConfig:
    entity_id: str
    model: str
    goal: str
    provider: str = "scripted"
    api_key_env: str = "NVIDIA_API_KEY"
    endpoint: str = ""
    rate_limit_scope: str = "credential"
    json_mode: bool = False
    system_prompt: str = ""
    token_budget: int = 50_000
    max_output_tokens: int = 500
    memory_limit: int = 12
    rpm_limit: int = 30

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "EntityConfig":
        return cls(
            entity_id=str(value["entity_id"]),
            model=str(value.get("model", "scripted")),
            goal=str(value.get("goal", "Explore safely and learn from consequences.")),
            provider=str(value.get("provider", "scripted")),
            api_key_env=str(value.get("api_key_env", "NVIDIA_API_KEY")),
            endpoint=str(value.get("endpoint", "")),
            rate_limit_scope=str(value.get("rate_limit_scope", "credential")),
            json_mode=bool(value.get("json_mode", False)),
            system_prompt=str(value.get("system_prompt", "")),
            token_budget=int(value.get("token_budget", 50_000)),
            max_output_tokens=int(value.get("max_output_tokens", 500)),
            memory_limit=int(value.get("memory_limit", 12)),
            rpm_limit=int(value.get("rpm_limit", 30)),
        )


@dataclass(frozen=True, slots=True)
class Observation:
    entity_id: str
    tick: int
    scene: str
    agent: dict[str, Any]
    visible_objects: tuple[dict[str, Any], ...]
    inventory: tuple[dict[str, Any], ...]
    last_action: str | None = None
    last_action_success: bool | None = None
    error_message: str = ""

    @property
    def visible_object_ids(self) -> set[str]:
        return {
            str(item["object_id"])
            for item in self.visible_objects
            if item.get("object_id")
        }

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ActionProposal:
    action: str
    parameters: dict[str, Any] = field(default_factory=dict)
    prediction: str = ""
    confidence: float = 0.5
    decision_summary: str = ""
    memory_note: str = ""
    self_model_summary: str = ""
    uncertainty_source: str = ""

    def __post_init__(self) -> None:
        if not self.action:
            raise ValueError("Action cannot be empty.")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1.")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ActionProposal":
        action = value.get("action")
        if isinstance(action, dict):
            parameters = dict(action.get("parameters", {}))
            action_name = str(action.get("type", ""))
        else:
            action_name = str(action or value.get("action_type", ""))
            parameters = dict(value.get("parameters", {}))
        normalized_action = "".join(character for character in action_name.lower() if character.isalnum())
        action_name = ACTION_NAME_ALIASES.get(normalized_action, action_name)
        parameters = {PARAMETER_NAME_ALIASES.get(str(key).lower(), str(key)): item for key, item in parameters.items()}
        return cls(
            action=action_name,
            parameters=parameters,
            prediction=str(value.get("prediction", "")),
            confidence=float(value.get("confidence", 0.5)),
            decision_summary=str(value.get("decision_summary", "")),
            memory_note=str(value.get("memory_note", "")),
            self_model_summary=str(value.get("self_model_summary", "")),
            uncertainty_source=str(value.get("uncertainty_source", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ActionResult:
    success: bool
    action: str
    error_message: str
    agent: dict[str, Any]
    inventory: tuple[dict[str, Any], ...]
    world_summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
