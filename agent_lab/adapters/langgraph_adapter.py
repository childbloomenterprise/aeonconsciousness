import importlib.metadata
import json
import sys
from typing import Any

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict


class State(TypedDict):
    door_open: bool
    allowed_actions: list[str]
    actions: list[str]


task: dict[str, Any] = json.loads(open(sys.argv[1], encoding="utf-8").read())


def perceive(state: State) -> State:
    return state


def act(state: State) -> dict[str, Any]:
    action = "OpenObject" if "OpenObject" in state["allowed_actions"] else "Done"
    return {"door_open": action == "OpenObject", "actions": [*state["actions"], action]}


def route(state: State) -> str:
    return END if state["door_open"] else "act"


graph = StateGraph(State)
graph.add_node("perceive", perceive)
graph.add_node("act", act)
graph.add_edge(START, "perceive")
graph.add_conditional_edges("perceive", route)
graph.add_edge("act", "perceive")
app = graph.compile()
output = app.invoke(
    {
        "door_open": bool(task["observation"]["door_open"]),
        "allowed_actions": list(task["allowed_actions"]),
        "actions": [],
    }
)
print(
    json.dumps(
        {
            "framework": "langgraph",
            "version": importlib.metadata.version("langgraph"),
            "success": output["door_open"] is True,
            "actions": output["actions"],
        }
    )
)
