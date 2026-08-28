from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import ActionProposal, Observation


ACTION_PARAMETERS: dict[str, set[str]] = {
    "MoveAhead": {"moveMagnitude"},
    "MoveBack": {"moveMagnitude"},
    "MoveLeft": {"moveMagnitude"},
    "MoveRight": {"moveMagnitude"},
    "RotateLeft": {"degrees"},
    "RotateRight": {"degrees"},
    "LookUp": {"degrees"},
    "LookDown": {"degrees"},
    "PickupObject": {"objectId"},
    "PutObject": {"objectId", "placeStationary"},
    "DropHandObject": set(),
    "OpenObject": {"objectId", "openness"},
    "CloseObject": {"objectId"},
    "ToggleObjectOn": {"objectId"},
    "ToggleObjectOff": {"objectId"},
    "SliceObject": {"objectId"},
    "Done": set(),
    "Wait": set(),
    "Inspect": set(),
    "SwimUp": set(),
    "GrabFloat": set(),
    "MoveToExit": set(),
    "CoolDown": set(),
    "Drink": set(),
    "Rest": set(),
    "SignalHelp": set(),
}

OBJECT_ACTIONS = {
    "PickupObject",
    "PutObject",
    "OpenObject",
    "CloseObject",
    "ToggleObjectOn",
    "ToggleObjectOff",
    "SliceObject",
}


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    allowed: bool
    reason: str
    action: dict[str, Any] | None = None


class ActionPolicy:
    """Deterministic action boundary. Model output never bypasses this class."""

    def __init__(self, allowed_actions: set[str] | None = None):
        self.allowed_actions = allowed_actions or set(ACTION_PARAMETERS)

    def validate(self, proposal: ActionProposal, observation: Observation) -> PolicyDecision:
        if proposal.action not in self.allowed_actions or proposal.action not in ACTION_PARAMETERS:
            return PolicyDecision(False, f"Action '{proposal.action}' is not permitted.")

        supplied = set(proposal.parameters)
        permitted = ACTION_PARAMETERS[proposal.action]
        extras = supplied - permitted
        if extras:
            return PolicyDecision(False, f"Unexpected parameters: {sorted(extras)}")

        parameters = dict(proposal.parameters)
        if proposal.action == "PickupObject" and observation.inventory:
            return PolicyDecision(False, "Cannot pick up another object while inventory is occupied.")
        if proposal.action in {"PutObject", "DropHandObject"} and not observation.inventory:
            return PolicyDecision(False, "Cannot place or drop an object when inventory is empty.")
        if proposal.action in OBJECT_ACTIONS:
            object_id = parameters.get("objectId")
            if not object_id:
                return PolicyDecision(False, "Object action requires objectId.")
            if str(object_id) not in observation.visible_object_ids:
                matches = [
                    str(item["object_id"])
                    for item in observation.visible_objects
                    if item.get("object_id")
                    and str(item.get("object_type", "")).casefold() == str(object_id).casefold()
                ]
                if len(matches) == 1:
                    object_id = matches[0]
                    parameters["objectId"] = object_id
            if str(object_id) not in observation.visible_object_ids:
                return PolicyDecision(False, "Object must be visible to the acting entity.")
            target = next(
                (item for item in observation.visible_objects if str(item.get("object_id")) == str(object_id)),
                None,
            )
            if proposal.action == "PickupObject" and (not target or not target.get("pickupable")):
                return PolicyDecision(False, "PickupObject objectId must identify a pickupable object.")
            if proposal.action == "PutObject":
                if not target or not target.get("receptacle"):
                    return PolicyDecision(False, "PutObject objectId must identify a visible receptacle.")

        if "moveMagnitude" in parameters:
            magnitude = float(parameters["moveMagnitude"])
            if not 0.0 < magnitude <= 1.0:
                return PolicyDecision(False, "moveMagnitude must be in (0, 1].")
            parameters["moveMagnitude"] = magnitude

        if "degrees" in parameters:
            degrees = float(parameters["degrees"])
            if degrees not in {30.0, 45.0, 90.0}:
                return PolicyDecision(False, "degrees must be 30, 45, or 90.")
            parameters["degrees"] = degrees

        if proposal.action == "OpenObject" and "openness" in parameters:
            openness = float(parameters["openness"])
            if not 0.0 <= openness <= 1.0:
                return PolicyDecision(False, "openness must be between 0 and 1.")
            parameters["openness"] = openness

        return PolicyDecision(True, "allowed", {"action": proposal.action, **parameters})
