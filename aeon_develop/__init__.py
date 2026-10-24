"""AEON developmental self-model: a small embodied agent that discovers its body,
questions its own self-model, treats thinking as an action, and records every
internal change. Numerical states are *internal estimates*; nothing here is a
claim of subjective experience."""

from .agent import Aeon, AeonConfig
from .world import ArmWorld

__all__ = ["Aeon", "AeonConfig", "ArmWorld"]
