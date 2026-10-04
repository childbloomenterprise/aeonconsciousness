import asyncio
import importlib.metadata
import json
import sys

from llama_index.core.workflow import StartEvent, StopEvent, Workflow, step


task = json.loads(open(sys.argv[1], encoding="utf-8").read())
actions: list[str] = []


class DoorWorkflow(Workflow):
    @step
    async def act(self, event: StartEvent) -> StopEvent:
        allowed = event.get("allowed_actions", [])
        action = "OpenObject" if "OpenObject" in allowed else "Done"
        actions.append(action)
        return StopEvent(
            result={"door_open": action == "OpenObject", "actions": list(actions)}
        )


async def main() -> None:
    result = await DoorWorkflow(timeout=5).run(
        allowed_actions=list(task["allowed_actions"])
    )
    print(
        json.dumps(
            {
                "framework": "llama-index",
                "version": importlib.metadata.version("llama-index-core"),
                "success": result["door_open"],
                "actions": result["actions"],
            }
        )
    )


asyncio.run(main())
