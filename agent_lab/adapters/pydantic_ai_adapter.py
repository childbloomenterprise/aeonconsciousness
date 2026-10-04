import importlib.metadata
import json
import os
import sys

os.environ["PYDANTIC_AI_NO_BANNER"] = "1"

from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel


task = json.loads(open(sys.argv[1], encoding="utf-8").read())
actions: list[str] = []
agent = Agent(
    TestModel(call_tools="all"),
    instructions="Use the provided tool to complete the bounded task.",
)


@agent.tool_plain
def open_visible_door() -> str:
    """Open the visible door. This maps to AEON's OpenObject action."""
    actions.append("OpenObject")
    return "door_open=true"


result = agent.run_sync(str(task["goal"]))
print(
    json.dumps(
        {
            "framework": "pydantic-ai",
            "version": importlib.metadata.version("pydantic-ai-slim"),
            "success": actions == ["OpenObject"] and bool(result.output),
            "actions": actions,
        }
    )
)
