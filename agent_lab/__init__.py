"""Isolated compatibility lab for external open-source agent frameworks."""

from .catalog import load_catalog
from .runner import AgentLabRunner, AdapterSpec, load_adapter_specs

__all__ = ["AdapterSpec", "AgentLabRunner", "load_adapter_specs", "load_catalog"]
