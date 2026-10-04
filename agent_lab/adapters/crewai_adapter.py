import importlib.metadata
import json
import os
import sys

from crewai.flow.flow import Flow, listen, start


task = json.loads(open(sys.argv[1], encoding="utf-8").read())


class DoorFlow(Flow):
    @start()
    def perceive(self):
        return {
            "door_open": bool(task["observation"]["door_open"]),
            "allowed_actions": list(task["allowed_actions"]),
        }

    @listen(perceive)
    def act(self, observation):
        action = "OpenObject" if "OpenObject" in observation["allowed_actions"] else "Done"
        return {
            "success": action == "OpenObject",
            "actions": [action],
            "door_open": action == "OpenObject",
        }


output = DoorFlow().kickoff()
result = json.dumps(
    {
        "framework": "crewai",
        "version": importlib.metadata.version("crewai"),
        "success": bool(output["success"]),
        "actions": output["actions"],
    }
)
# CrewAI's trace renderer captures normal stdout. Write the machine contract
# directly to fd 1 so the parent runner always receives a standalone JSON line.
os.write(1, (result + "\n").encode("utf-8"))
