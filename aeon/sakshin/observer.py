from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from aeon.core.contracts import new_id
from aeon.storage.local import LocalStorage


class SakshinObserver:
    """Read-only observer: accepts storage without mutation methods in public workflow."""

    def __init__(self, storage: LocalStorage) -> None:
        self._storage = storage

    def witness(self, cycle_id: str, self_report: dict[str, Any]) -> dict[str, Any]:
        events = [event for event in self._storage.list_events() if event.cycle_id == cycle_id]
        retrieved = {
            ref
            for event in events
            if event.event_type == "memory_retrieved"
            for ref in event.memory_refs
        }
        claimed = set(self_report.get("memory_refs", []))
        missing = sorted(claimed - retrieved)
        chain = self._storage.verify_event_chain()
        status = "CONSISTENT"
        if not chain["valid"]:
            status = "POSSIBLE_TAMPERING"
        elif missing:
            status = "POSSIBLE_CONFABULATION"
        elif len(events) < 5:
            status = "INSUFFICIENT_TELEMETRY"
        report = {
            "report_id": new_id("witness"),
            "cycle_id": cycle_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "status": status,
            "event_count": len(events),
            "telemetry_coverage": min(1.0, len(events) / 10),
            "observer_lag_ms": 0,
            "claimed_memory_refs": sorted(claimed),
            "observed_memory_refs": sorted(retrieved),
            "mismatches": [{"type": "source_attribution", "memory_id": ref} for ref in missing],
            "event_chain": chain,
        }
        self._storage.write_record("witness", report)
        return report
