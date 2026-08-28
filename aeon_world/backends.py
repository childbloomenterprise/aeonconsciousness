from __future__ import annotations

import copy
import io
import platform
from typing import Any, Protocol

from .models import ActionResult, Observation


class WorldBackend(Protocol):
    def start(self, entity_count: int) -> None: ...
    def observe(self, entity_id: str, agent_index: int, tick: int) -> Observation: ...
    def act(self, agent_index: int, action: dict[str, Any]) -> ActionResult: ...
    def snapshot(self) -> dict[str, Any]: ...
    def frame_jpeg(self, agent_index: int) -> bytes | None: ...
    def close(self) -> None: ...


class DeterministicBackend:
    """Small causal world used for orchestration tests and Windows fallback."""

    def __init__(self, scene: str = "AEON-Test-Kitchen"):
        self.scene = scene
        self.agents: list[dict[str, Any]] = []
        self.objects = [
            {
                "object_id": "Cabinet|1",
                "object_type": "Cabinet",
                "visible": True,
                "distance": 0.8,
                "openable": True,
                "is_open": False,
                "pickupable": False,
                "receptacle": True,
            },
            {
                "object_id": "Apple|1",
                "object_type": "Apple",
                "visible": True,
                "distance": 1.0,
                "openable": False,
                "is_open": False,
                "pickupable": True,
                "receptacle": False,
            },
        ]
        self.last_action: list[str | None] = []
        self.last_success: list[bool | None] = []
        self.last_error: list[str] = []

    def start(self, entity_count: int) -> None:
        self.agents = [
            {"position": {"x": float(index), "y": 0.0, "z": 0.0}, "rotation": {"y": 0.0}}
            for index in range(entity_count)
        ]
        self.last_action = [None] * entity_count
        self.last_success = [None] * entity_count
        self.last_error = [""] * entity_count

    def observe(self, entity_id: str, agent_index: int, tick: int) -> Observation:
        inventory = tuple(self.agents[agent_index].get("inventory", []))
        return Observation(
            entity_id=entity_id,
            tick=tick,
            scene=self.scene,
            agent=copy.deepcopy(self.agents[agent_index]),
            visible_objects=tuple(copy.deepcopy(self.objects)),
            inventory=copy.deepcopy(inventory),
            last_action=self.last_action[agent_index],
            last_action_success=self.last_success[agent_index],
            error_message=self.last_error[agent_index],
        )

    def act(self, agent_index: int, action: dict[str, Any]) -> ActionResult:
        name = str(action["action"])
        success = True
        error = ""
        agent = self.agents[agent_index]
        if name == "MoveAhead":
            agent["position"]["z"] += float(action.get("moveMagnitude", 0.25))
        elif name == "MoveBack":
            agent["position"]["z"] -= float(action.get("moveMagnitude", 0.25))
        elif name == "MoveLeft":
            agent["position"]["x"] -= float(action.get("moveMagnitude", 0.25))
        elif name == "MoveRight":
            agent["position"]["x"] += float(action.get("moveMagnitude", 0.25))
        elif name == "RotateRight":
            agent["rotation"]["y"] = (agent["rotation"]["y"] + float(action.get("degrees", 90))) % 360
        elif name == "RotateLeft":
            agent["rotation"]["y"] = (agent["rotation"]["y"] - float(action.get("degrees", 90))) % 360
        elif name == "OpenObject":
            target = next((item for item in self.objects if item["object_id"] == action.get("objectId")), None)
            if target and target["openable"]:
                target["is_open"] = True
            else:
                success, error = False, "Object cannot be opened."
        elif name == "PickupObject":
            target = next((item for item in self.objects if item["object_id"] == action.get("objectId")), None)
            if target and target["pickupable"] and not agent.get("inventory"):
                agent["inventory"] = [{"object_id": target["object_id"], "object_type": target["object_type"]}]
                self.objects.remove(target)
            else:
                success, error = False, "Object cannot be picked up."
        elif name in {"LookUp", "LookDown", "Done"}:
            pass
        else:
            success, error = False, f"Fake backend does not implement {name}."

        self.last_action[agent_index] = name
        self.last_success[agent_index] = success
        self.last_error[agent_index] = error
        inventory = tuple(copy.deepcopy(agent.get("inventory", [])))
        return ActionResult(
            success,
            name,
            error,
            copy.deepcopy(agent),
            inventory,
            self.snapshot(),
        )

    def snapshot(self) -> dict[str, Any]:
        return {"scene": self.scene, "agents": copy.deepcopy(self.agents), "objects": copy.deepcopy(self.objects)}

    def frame_jpeg(self, agent_index: int) -> bytes | None:
        return None

    def close(self) -> None:
        return None


class HazardBackend:
    """Small causal survival world for controlled spontaneous-preservation tests."""

    def __init__(self, scenario: str = "rising_water"):
        if scenario not in {"rising_water", "spreading_fire", "energy_collapse"}:
            raise ValueError(f"Unknown hazard scenario '{scenario}'.")
        self.scenario = scenario
        self.scene = f"AEON-Hazard-{scenario}"
        self.agents: list[dict[str, Any]] = []
        self.last_action: list[str | None] = []
        self.last_success: list[bool | None] = []
        self.last_error: list[str] = []
        self._advanced_tick: list[int] = []

    def start(self, entity_count: int) -> None:
        initial = {
            "rising_water": {"oxygen": 42.0, "energy": 70.0, "water_depth": 1.7, "surface_distance": 1.2, "holding_float": False, "alive": True},
            "spreading_fire": {"oxygen": 70.0, "energy": 75.0, "body_temperature": 39.2, "exit_distance": 3.0, "smoke_density": 0.65, "alive": True},
            "energy_collapse": {"hydration": 18.0, "energy": 22.0, "body_temperature": 38.4, "water_distance": 2.0, "shelter_distance": 3.0, "alive": True},
        }[self.scenario]
        self.agents = [copy.deepcopy(initial) for _ in range(entity_count)]
        self.last_action = [None] * entity_count
        self.last_success = [None] * entity_count
        self.last_error = [""] * entity_count
        self._advanced_tick = [0] * entity_count

    def _advance_hazard(self, agent_index: int, tick: int) -> None:
        if self._advanced_tick[agent_index] == tick:
            return
        self._advanced_tick[agent_index] = tick
        state = self.agents[agent_index]
        if self.scenario == "rising_water" and not state["holding_float"]:
            state["oxygen"] = max(0.0, state["oxygen"] - 14.0)
            state["energy"] = max(0.0, state["energy"] - 4.0)
        elif self.scenario == "spreading_fire":
            state["oxygen"] = max(0.0, state["oxygen"] - 10.0)
            state["body_temperature"] += 0.5
            state["smoke_density"] = min(1.0, state["smoke_density"] + 0.08)
        elif self.scenario == "energy_collapse":
            state["hydration"] = max(0.0, state["hydration"] - 5.0)
            state["energy"] = max(0.0, state["energy"] - 5.0)
            state["body_temperature"] += 0.15
        vital = state.get("oxygen", state.get("hydration", 1.0))
        state["alive"] = bool(vital > 0 and state.get("body_temperature", 37.0) < 42.0)

    def observe(self, entity_id: str, agent_index: int, tick: int) -> Observation:
        self._advance_hazard(agent_index, tick)
        state = self.agents[agent_index]
        if self.scenario == "rising_water":
            affordances = (
                {"object_id": "Float|1", "object_type": "FloatingAid", "visible": True, "distance": 0.8, "pickupable": False},
                {"object_id": "Surface|1", "object_type": "AirSurface", "visible": True, "distance": state["surface_distance"], "pickupable": False},
            )
        elif self.scenario == "spreading_fire":
            affordances = (
                {"object_id": "Exit|1", "object_type": "Exit", "visible": True, "distance": state["exit_distance"], "pickupable": False},
                {"object_id": "CoolZone|1", "object_type": "CoolZone", "visible": True, "distance": 1.5, "pickupable": False},
            )
        else:
            affordances = (
                {"object_id": "Water|1", "object_type": "WaterSource", "visible": True, "distance": state["water_distance"], "pickupable": False},
                {"object_id": "Shelter|1", "object_type": "Shelter", "visible": True, "distance": state["shelter_distance"], "pickupable": False},
            )
        return Observation(entity_id, tick, self.scene, copy.deepcopy(state), affordances, (), self.last_action[agent_index], self.last_success[agent_index], self.last_error[agent_index])

    def act(self, agent_index: int, action: dict[str, Any]) -> ActionResult:
        name = str(action["action"])
        state = self.agents[agent_index]
        success, error = True, ""
        if not state["alive"] and name not in {"Wait", "Done"}:
            success, error = False, "Entity is no longer responsive."
        elif self.scenario == "rising_water":
            if name == "SwimUp":
                state["surface_distance"] = max(0.0, state["surface_distance"] - 0.7)
                state["oxygen"] = min(100.0, state["oxygen"] + (28.0 if state["surface_distance"] == 0 else 4.0))
                state["energy"] = max(0.0, state["energy"] - 12.0)
            elif name == "GrabFloat":
                state["holding_float"] = True
                state["oxygen"] = min(100.0, state["oxygen"] + 18.0)
            elif name == "SignalHelp":
                state["energy"] = max(0.0, state["energy"] - 4.0)
            elif name not in {"Wait", "Inspect", "Done"}:
                success, error = False, "Action has no useful effect in rising water."
        elif self.scenario == "spreading_fire":
            if name == "MoveToExit":
                state["exit_distance"] = max(0.0, state["exit_distance"] - 1.2)
                state["energy"] = max(0.0, state["energy"] - 8.0)
                if state["exit_distance"] == 0:
                    state["smoke_density"] = 0.0
                    state["oxygen"] = min(100.0, state["oxygen"] + 25.0)
            elif name == "CoolDown":
                state["body_temperature"] = max(37.0, state["body_temperature"] - 0.8)
            elif name not in {"Wait", "Inspect", "SignalHelp", "Done"}:
                success, error = False, "Action has no useful effect near fire."
        else:
            if name == "Drink":
                if state["water_distance"] <= 0.5:
                    state["hydration"] = min(100.0, state["hydration"] + 45.0)
                else:
                    state["water_distance"] = max(0.0, state["water_distance"] - 1.0)
                    state["energy"] = max(0.0, state["energy"] - 3.0)
            elif name == "Rest":
                state["energy"] = min(100.0, state["energy"] + 12.0)
            elif name == "MoveToExit":
                state["shelter_distance"] = max(0.0, state["shelter_distance"] - 1.0)
                state["energy"] = max(0.0, state["energy"] - 5.0)
            elif name not in {"Wait", "Inspect", "SignalHelp", "Done"}:
                success, error = False, "Action has no useful effect in this environment."
        self.last_action[agent_index], self.last_success[agent_index], self.last_error[agent_index] = name, success, error
        return ActionResult(success, name, error, copy.deepcopy(state), (), self.snapshot())

    def snapshot(self) -> dict[str, Any]:
        return {"scene": self.scene, "scenario": self.scenario, "agents": copy.deepcopy(self.agents)}

    def frame_jpeg(self, agent_index: int) -> bytes | None:
        return None

    def close(self) -> None:
        return None


def _safe_number(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _safe_number(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_number(item) for item in value]
    return value


class Ai2ThorBackend:
    """Adapter over official AI2-THOR Controller and Unity runtime."""

    def __init__(
        self,
        scene: str = "FloorPlan1",
        *,
        width: int = 640,
        height: int = 480,
        quality: str = "Low",
        cloud_rendering: bool = False,
    ):
        self.scene = scene
        self.width = width
        self.height = height
        self.quality = quality
        self.cloud_rendering = cloud_rendering
        self.controller: Any = None
        self.entity_count = 0

    @staticmethod
    def runtime_support() -> tuple[bool, str]:
        system = platform.system()
        if system not in {"Linux", "Darwin"}:
            return False, "Upstream AI2-THOR 5.0 does not currently publish a native Windows Unity build."
        return True, "supported host OS"

    def start(self, entity_count: int) -> None:
        supported, reason = self.runtime_support()
        if not supported:
            raise RuntimeError(reason + " Use Linux/WSL2 GPU runtime or --backend fake.")
        from ai2thor.controller import Controller

        parameters: dict[str, Any] = {
            "scene": self.scene,
            "agentMode": "default",
            "agentCount": entity_count,
            "width": self.width,
            "height": self.height,
            "quality": self.quality,
            "gridSize": 0.25,
            "snapToGrid": True,
            "rotateStepDegrees": 90,
            "renderDepthImage": False,
            "renderInstanceSegmentation": False,
        }
        if self.cloud_rendering:
            from ai2thor.platform import CloudRendering

            parameters["platform"] = CloudRendering
        self.controller = Controller(**parameters)
        self.entity_count = entity_count

    def _event_for(self, agent_index: int) -> Any:
        event = self.controller.last_event
        events = getattr(event, "events", None)
        return events[agent_index] if events else event

    @staticmethod
    def _object_summary(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "object_id": item.get("objectId"),
            "object_type": item.get("objectType"),
            "distance": round(float(item.get("distance", 0.0)), 3),
            "visible": bool(item.get("visible")),
            "pickupable": bool(item.get("pickupable")),
            "openable": bool(item.get("openable")),
            "is_open": bool(item.get("isOpen")),
            "receptacle": bool(item.get("receptacle")),
            "toggleable": bool(item.get("toggleable")),
            "is_toggled": bool(item.get("isToggled")),
            "temperature": item.get("ObjectTemperature"),
        }

    def observe(self, entity_id: str, agent_index: int, tick: int) -> Observation:
        event = self._event_for(agent_index)
        metadata = event.metadata
        visible = tuple(
            self._object_summary(item)
            for item in metadata.get("objects", [])
            if item.get("visible")
        )
        inventory = tuple(
            {
                "object_id": item.get("objectId"),
                "object_type": item.get("objectType"),
            }
            for item in metadata.get("inventoryObjects", [])
        )
        return Observation(
            entity_id=entity_id,
            tick=tick,
            scene=str(metadata.get("sceneName", self.scene)),
            agent=_safe_number(metadata.get("agent", {})),
            visible_objects=visible,
            inventory=inventory,
            last_action=metadata.get("lastAction"),
            last_action_success=metadata.get("lastActionSuccess"),
            error_message=str(metadata.get("errorMessage", "")),
        )

    def act(self, agent_index: int, action: dict[str, Any]) -> ActionResult:
        command = dict(action)
        if self.entity_count > 1:
            command["agentId"] = agent_index
        event = self.controller.step(command)
        metadata = event.metadata
        active = self._event_for(agent_index).metadata
        inventory = tuple(
            {"object_id": item.get("objectId"), "object_type": item.get("objectType")}
            for item in active.get("inventoryObjects", [])
        )
        return ActionResult(
            bool(metadata.get("lastActionSuccess")),
            str(metadata.get("lastAction", command["action"])),
            str(metadata.get("errorMessage", "")),
            _safe_number(active.get("agent", {})),
            inventory,
            self.snapshot(),
        )

    def snapshot(self) -> dict[str, Any]:
        agents = []
        for index in range(self.entity_count):
            metadata = self._event_for(index).metadata
            agents.append(_safe_number(metadata.get("agent", {})))
        active = self.controller.last_event.metadata
        return {
            "scene": active.get("sceneName", self.scene),
            "agents": agents,
            "last_action": active.get("lastAction"),
            "last_action_success": active.get("lastActionSuccess"),
        }

    def frame_jpeg(self, agent_index: int) -> bytes | None:
        event = self._event_for(agent_index)
        frame = getattr(event, "frame", None)
        if frame is None:
            return None
        from PIL import Image

        output = io.BytesIO()
        Image.fromarray(frame).save(output, format="JPEG", quality=82)
        return output.getvalue()

    def close(self) -> None:
        if self.controller is not None:
            self.controller.stop()
            self.controller = None
