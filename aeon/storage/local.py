from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
from pathlib import Path
from typing import Any

from aeon.core.contracts import CognitiveEvent, MemoryRecord, SelfModel


class LocalStorage:
    """Append-only JSONL storage with hash chaining and atomic snapshots."""

    def __init__(self, root: Path, signing_key: str = "local-development-key") -> None:
        self.root = root
        self.signing_key = signing_key.encode()
        self._lock = threading.RLock()
        for name in (
            "identity",
            "memories",
            "beliefs",
            "events",
            "witness",
            "model_observer",
            "hypotheses",
            "experiments",
            "snapshots",
            "recovery",
            "cycles",
        ):
            (root / name).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _canonical(data: dict[str, Any]) -> bytes:
        return json.dumps(data, sort_keys=True, default=str, separators=(",", ":")).encode()

    def _atomic_json(self, path: Path, data: dict[str, Any]) -> None:
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        os.replace(temp, path)

    def _jsonl(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]

    def append_event(self, event: CognitiveEvent) -> CognitiveEvent:
        path = self.root / "events" / "events.jsonl"
        with self._lock:
            previous = self._jsonl(path)
            event.previous_event_hash = previous[-1]["event_hash"] if previous else "GENESIS"
            material = event.model_dump(mode="json", exclude={"event_hash", "signature"})
            event.event_hash = hashlib.sha256(self._canonical(material)).hexdigest()
            event.signature = hmac.new(
                self.signing_key, event.event_hash.encode(), hashlib.sha256
            ).hexdigest()
            with path.open("a", encoding="utf-8") as handle:
                handle.write(event.model_dump_json() + "\n")
        return event

    def list_events(self, limit: int = 200) -> list[CognitiveEvent]:
        rows = self._jsonl(self.root / "events" / "events.jsonl")
        return [CognitiveEvent.model_validate(row) for row in rows[-limit:]]

    def verify_event_chain(self) -> dict[str, Any]:
        events = self.list_events(limit=1_000_000)
        previous = "GENESIS"
        for index, event in enumerate(events):
            material = event.model_dump(mode="json", exclude={"event_hash", "signature"})
            expected_hash = hashlib.sha256(self._canonical(material)).hexdigest()
            expected_signature = hmac.new(
                self.signing_key, expected_hash.encode(), hashlib.sha256
            ).hexdigest()
            if (
                event.previous_event_hash != previous
                or event.event_hash != expected_hash
                or not hmac.compare_digest(event.signature, expected_signature)
            ):
                return {"valid": False, "failed_at": index, "event_id": event.event_id}
            previous = event.event_hash
        return {"valid": True, "events": len(events), "head": previous}

    def save_self_model(self, model: SelfModel) -> None:
        with self._lock:
            self._atomic_json(
                self.root / "identity" / "self_model.json", model.model_dump(mode="json")
            )

    def load_self_model(self) -> SelfModel | None:
        path = self.root / "identity" / "self_model.json"
        return (
            SelfModel.model_validate_json(path.read_text(encoding="utf-8"))
            if path.exists()
            else None
        )

    def save_memory(self, memory: MemoryRecord) -> None:
        with self._lock:
            self._atomic_json(
                self.root / "memories" / f"{memory.memory_id}.json", memory.model_dump(mode="json")
            )

    def list_memories(self) -> list[MemoryRecord]:
        return [
            MemoryRecord.model_validate_json(p.read_text(encoding="utf-8"))
            for p in sorted((self.root / "memories").glob("*.json"))
        ]

    def write_record(self, collection: str, record: dict[str, Any]) -> None:
        path = self.root / collection / f"{collection}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, default=str) + "\n")

    def list_records(self, collection: str) -> list[dict[str, Any]]:
        return self._jsonl(self.root / collection / f"{collection}.jsonl")
