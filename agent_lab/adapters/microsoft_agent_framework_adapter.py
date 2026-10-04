import asyncio
import importlib.metadata
import json
import sys

from agent_framework import WorkflowBuilder, WorkflowContext, executor
from typing_extensions import Never


task = json.loads(open(sys.argv[1], encoding="utf-8").read())
actions: list[str] = []


@executor(id="aeon_action")
async def act(observation: dict, ctx: WorkflowContext[Never, dict]) -> None:
    allowed = observation.get("allowed_actions", [])
    action = "OpenObject" if "OpenObject" in allowed else "Done"
    actions.append(action)
    await ctx.yield_output(
        {"door_open": action == "OpenObject", "actions": list(actions)}
    )


async def main() -> None:
    workflow = WorkflowBuilder(start_executor=act).build()
    events = await workflow.run(task)
    result = events.get_outputs()[0]
    print(
        json.dumps(
            {
                "framework": "microsoft-agent-framework",
                "version": importlib.metadata.version("agent-framework-core"),
                "success": result["door_open"],
                "actions": result["actions"],
            }
        )
    )


asyncio.run(main())
