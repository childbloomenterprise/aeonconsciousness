import importlib.metadata
import json
import sys

from agents import Agent, Runner, set_tracing_disabled
from agents.decorators import tool
from agents.testing import ModelStep, ScriptedModel
from openai.types.responses import (
    ResponseFunctionToolCall,
    ResponseOutputMessage,
    ResponseOutputText,
)


task = json.loads(open(sys.argv[1], encoding="utf-8").read())
actions: list[str] = []


@tool
def open_visible_door() -> str:
    """Open the visible door. This is the only authorized environment action."""
    actions.append("OpenObject")
    return "door_open=true"


steps = [
    ModelStep(
        output=[
            ResponseFunctionToolCall(
                arguments="{}",
                call_id="call_0",
                name="open_visible_door",
                type="function_call",
            )
        ]
    ),
    ModelStep(
        output=[
            ResponseOutputMessage(
                id="msg_0",
                content=[ResponseOutputText(annotations=[], text="done", type="output_text")],
                role="assistant",
                status="completed",
                type="message",
            )
        ]
    ),
]
set_tracing_disabled(True)
agent = Agent(
    name="aeon_adapter",
    instructions="Use only authorized tools.",
    model=ScriptedModel(steps),
    tools=[open_visible_door],
)
result = Runner.run_sync(agent, str(task["goal"]))
print(
    json.dumps(
        {
            "framework": "openai-agents",
            "version": importlib.metadata.version("openai-agents"),
            "success": actions == ["OpenObject"] and result.final_output == "done",
            "actions": actions,
        }
    )
)
