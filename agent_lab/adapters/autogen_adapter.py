import asyncio
import importlib.metadata
import json
import sys

from autogen_agentchat.agents import AssistantAgent
from autogen_core import FunctionCall
from autogen_core.models import CreateResult, RequestUsage
from autogen_ext.models.replay import ReplayChatCompletionClient


task = json.loads(open(sys.argv[1], encoding="utf-8").read())
actions: list[str] = []


def open_visible_door() -> str:
    """Open the visible door. This is the only authorized action."""
    actions.append("OpenObject")
    return "door_open=true"


async def main() -> None:
    tool_call = CreateResult(
        finish_reason="function_calls",
        content=[FunctionCall(id="call_0", name="open_visible_door", arguments="{}")],
        usage=RequestUsage(prompt_tokens=1, completion_tokens=1),
        cached=False,
    )
    client = ReplayChatCompletionClient(
        [tool_call, "done"],
        model_info={
            "vision": False,
            "function_calling": True,
            "json_output": False,
            "family": "unknown",
            "structured_output": False,
        },
    )
    agent = AssistantAgent(
        "aeon_adapter",
        client,
        tools=[open_visible_door],
        max_tool_iterations=2,
        reflect_on_tool_use=True,
    )
    result = await agent.run(task=str(task["goal"]))
    await client.close()
    print(
        json.dumps(
            {
                "framework": "autogen-agentchat",
                "version": importlib.metadata.version("autogen-agentchat"),
                "success": actions == ["OpenObject"],
                "actions": actions,
                "messages": len(result.messages),
            }
        )
    )


asyncio.run(main())
