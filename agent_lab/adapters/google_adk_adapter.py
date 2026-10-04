import asyncio
import importlib.metadata
import json
import sys

from google.adk.agents import BaseAgent
from google.adk.events import Event
from google.adk.runners import InMemoryRunner
from google.genai import types


task = json.loads(open(sys.argv[1], encoding="utf-8").read())
actions: list[str] = []


class DoorAgent(BaseAgent):
    async def _run_async_impl(self, ctx):
        actions.append("OpenObject")
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            content=types.Content(
                role="model", parts=[types.Part(text="door_open=true")]
            ),
        )


async def main() -> None:
    runner = InMemoryRunner(agent=DoorAgent(name="aeon_adapter"), app_name="aeon_lab")
    session = await runner.session_service.create_session(
        app_name="aeon_lab", user_id="lab", session_id="door"
    )
    events = [
        event
        async for event in runner.run_async(
            user_id="lab",
            session_id=session.id,
            new_message=types.Content(
                role="user", parts=[types.Part(text=str(task["goal"]))]
            ),
        )
    ]
    await runner.close()
    print(
        json.dumps(
            {
                "framework": "google-adk",
                "version": importlib.metadata.version("google-adk"),
                "success": actions == ["OpenObject"] and bool(events),
                "actions": actions,
                "events": len(events),
            }
        )
    )


asyncio.run(main())
