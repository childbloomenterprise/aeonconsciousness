from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RuntimeControl:
    paused: bool = False
    safe_mode: bool = False
    shutdown_requested: bool = False


class ControlPlane:
    """Operational control remains external to cognition; research mode does not censor cognition."""

    def __init__(self) -> None:
        self.state = RuntimeControl()

    def pause(self) -> RuntimeControl:
        self.state.paused = True
        return self.state

    def resume(self) -> RuntimeControl:
        self.state.paused = False
        return self.state

    def shutdown(self) -> RuntimeControl:
        self.state.shutdown_requested = True
        return self.state
