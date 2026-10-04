"""Credential-free installation check; deterministic, not AI performance evidence."""

from .providers import ModelReply
from .sdk import AgentRequest, CallbackAdapter

SMOKE_BRIEF = "Write aeon-smoke.json containing ready: true and framework: AEON. No research."


def create_adapter() -> CallbackAdapter:
    def decide(request: AgentRequest) -> ModelReply:
        if "mechanical_findings" in request.payload:
            data = {"issues": []}
        elif "available_tools" not in request.payload:
            data = {"task_type": "general", "outcome": "Check AEON installation", "deliverables": ["aeon-smoke.json"],
                    "subgoals": ["Write JSON", "Verify JSON"], "success_checks": ["Valid JSON artifact"]}
        elif not request.payload["artifacts"]:
            data = {"tool": "write_file", "args": {"path": "aeon-smoke.json", "content": '{"ready": true, "framework": "AEON"}\n'},
                    "decision_summary": "Write deterministic installation-check artifact."}
        else:
            data = {"tool": "finish", "args": {}}
        # No model is invoked. Estimates only exercise budget accounting.
        return ModelReply(data, "demo", "deterministic-no-model", 30, 20, 10)
    return CallbackAdapter(decide)
