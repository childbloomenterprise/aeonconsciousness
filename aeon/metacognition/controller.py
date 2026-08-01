from aeon.core.contracts import ControlSignal, MetacognitiveReport


class MetacognitiveController:
    def intervene(self, report: MetacognitiveReport) -> dict[str, object]:
        actions = {
            ControlSignal.CONTINUE: "continue recurrent processing",
            ControlSignal.RETRIEVE: "expand memory retrieval",
            ControlSignal.VERIFY: "run contradiction verification",
            ControlSignal.CHANGE_STRATEGY: "switch synthesis strategy",
            ControlSignal.REDUCE_CONFIDENCE: "calibrate confidence downward",
            ControlSignal.ABSTAIN: "withhold unsupported conclusion",
            ControlSignal.REQUEST_CLARIFICATION: "request missing task constraints",
            ControlSignal.ENTER_VI_MODE: "quarantine reflective hypotheses",
        }
        return {
            "trigger": report.control_signal,
            "action": actions[report.control_signal],
            "expected_benefit": 0.2 if report.control_signal != ControlSignal.CONTINUE else 0.05,
        }
