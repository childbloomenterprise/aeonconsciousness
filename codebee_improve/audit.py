from __future__ import annotations

import hashlib
import json
import threading
import uuid
from pathlib import Path
from typing import Any

from .storage import atomic_write_text, file_lock, iso_now


class AuditLog:
    """Append-only, hash-chained audit log with deterministic verification."""

    def __init__(self, path: Path):
        self.path = path
        self.lock_path = path.with_suffix(path.suffix + ".lock")
        self._lock = threading.RLock()

    @staticmethod
    def _digest(event: dict[str, Any]) -> str:
        body = json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(body.encode("utf-8")).hexdigest()

    def events(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [
            json.loads(line)
            for line in self.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def append(self, event_type: str, *, actor: str, details: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            with file_lock(self.lock_path):
                events = self.events()
                event = {
                    "id": uuid.uuid4().hex,
                    "timestamp": iso_now(),
                    "type": event_type,
                    "actor": actor,
                    "details": details,
                    "previous_hash": events[-1]["hash"] if events else "GENESIS",
                }
                event["hash"] = self._digest(event)
                lines = [json.dumps(item, sort_keys=True, ensure_ascii=False) for item in [*events, event]]
                atomic_write_text(self.path, "\n".join(lines) + "\n")
                return event

    def verify(self) -> bool:
        previous = "GENESIS"
        try:
            for event in self.events():
                stored_hash = event.get("hash")
                unsigned = dict(event)
                unsigned.pop("hash", None)
                if event.get("previous_hash") != previous:
                    return False
                if stored_hash != self._digest(unsigned):
                    return False
                previous = stored_hash
            return True
        except (KeyError, ValueError, json.JSONDecodeError):
            return False
