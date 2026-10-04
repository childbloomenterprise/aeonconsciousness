import importlib.metadata
import json
import sys

from smolagents import ToolCallingAgent, tool
from smolagents.models import (
    ChatMessage,
    ChatMessageToolCall,
    ChatMessageToolCallFunction,
    MessageRole,
    Model,
)


task = json.loads(open(sys.argv[1], encoding="utf-8").read())
actions: list[str] = []


@tool
def open_visible_door() -> str:
    """Open the visible door.

    Returns:
        Updated door state.
    """
    actions.append("OpenObject")
    return "door_open=true"


class AeonModel(Model):
    def __init__(self):
        self.calls = 0

    def generate(self, messages, tools_to_call_from=None, stop_sequences=None, **kwargs):
        self.calls += 1
        if self.calls == 1:
            call = ChatMessageToolCall(
                id="call_0",
                type="function",
                function=ChatMessageToolCallFunction(name="open_visible_door", arguments={}),
            )
        else:
            call = ChatMessageToolCall(
                id="call_1",
                type="function",
                function=ChatMessageToolCallFunction(
                    name="final_answer", arguments={"answer": "done"}
                ),
            )
        return ChatMessage(role=MessageRole.ASSISTANT, content="", tool_calls=[call])


agent = ToolCallingAgent(
    tools=[open_visible_door], model=AeonModel(), verbosity_level=-1, max_steps=3
)
output = agent.run(str(task["goal"]))
print(
    json.dumps(
        {
            "framework": "smolagents",
            "version": importlib.metadata.version("smolagents"),
            "success": actions == ["OpenObject"] and str(output) == "done",
            "actions": actions,
        }
    )
)
