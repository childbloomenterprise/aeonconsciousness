from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_runtime_root() -> Path:
    import os

    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "AEON" / "runs"
    return Path.home() / ".local" / "share" / "aeon" / "runs"


class EventLedger:
    """SQLite event store with independent per-run hash chains."""

    def __init__(self, run_dir: Path):
        self.run_dir = Path(run_dir).resolve()
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.frames_dir = self.run_dir / "frames"
        self.frames_dir.mkdir(exist_ok=True)
        self.path = self.run_dir / "events.sqlite3"
        self.control_path = self.run_dir / "control.json"
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        return connection

    @contextmanager
    def _connection(self):
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    tick INTEGER NOT NULL DEFAULT 0,
                    config_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    run_id TEXT NOT NULL,
                    tick INTEGER NOT NULL,
                    entity_id TEXT,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES runs(run_id)
                );
                CREATE INDEX IF NOT EXISTS idx_events_run_sequence
                    ON events(run_id, sequence);
                CREATE INDEX IF NOT EXISTS idx_events_run_entity
                    ON events(run_id, entity_id, sequence);
                """
            )

    def start_run(self, run_id: str, config: dict[str, Any]) -> None:
        now = utc_now()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO runs(run_id, started_at, updated_at, status, tick, config_json)
                VALUES (?, ?, ?, 'running', 0, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    updated_at=excluded.updated_at,
                    status='running',
                    config_json=excluded.config_json
                """,
                (run_id, now, now, json.dumps(config, sort_keys=True)),
            )

    def update_run(self, run_id: str, *, tick: int, status: str) -> None:
        with self._connection() as connection:
            connection.execute(
                "UPDATE runs SET tick=?, status=?, updated_at=? WHERE run_id=?",
                (tick, status, utc_now(), run_id),
            )

    @staticmethod
    def _digest(event: dict[str, Any]) -> str:
        canonical = json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def append(
        self,
        run_id: str,
        tick: int,
        event_type: str,
        payload: dict[str, Any],
        *,
        entity_id: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            with self._connection() as connection:
                previous_row = connection.execute(
                    "SELECT event_hash FROM events WHERE run_id=? ORDER BY sequence DESC LIMIT 1",
                    (run_id,),
                ).fetchone()
                event = {
                    "event_id": uuid.uuid4().hex,
                    "run_id": run_id,
                    "tick": tick,
                    "entity_id": entity_id,
                    "event_type": event_type,
                    "payload": payload,
                    "previous_hash": previous_row["event_hash"] if previous_row else "GENESIS",
                    "created_at": utc_now(),
                }
                event["event_hash"] = self._digest(event)
                connection.execute(
                    """
                    INSERT INTO events(
                        event_id, run_id, tick, entity_id, event_type, payload_json,
                        previous_hash, event_hash, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event["event_id"],
                        run_id,
                        tick,
                        entity_id,
                        event_type,
                        json.dumps(payload, sort_keys=True, ensure_ascii=False),
                        event["previous_hash"],
                        event["event_hash"],
                        event["created_at"],
                    ),
                )
                return event

    def events(self, run_id: str | None = None, *, limit: int = 200) -> list[dict[str, Any]]:
        query = "SELECT * FROM events"
        values: tuple[Any, ...] = ()
        if run_id:
            query += " WHERE run_id=?"
            values = (run_id,)
        query += " ORDER BY sequence DESC LIMIT ?"
        values = (*values, limit)
        with self._connection() as connection:
            rows = connection.execute(query, values).fetchall()
        return [
            {
                "sequence": row["sequence"],
                "event_id": row["event_id"],
                "run_id": row["run_id"],
                "tick": row["tick"],
                "entity_id": row["entity_id"],
                "event_type": row["event_type"],
                "payload": json.loads(row["payload_json"]),
                "previous_hash": row["previous_hash"],
                "event_hash": row["event_hash"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def latest_run(self) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM runs ORDER BY updated_at DESC LIMIT 1").fetchone()
        if row is None:
            return None
        return {
            "run_id": row["run_id"],
            "started_at": row["started_at"],
            "updated_at": row["updated_at"],
            "status": row["status"],
            "tick": row["tick"],
            "config": json.loads(row["config_json"]),
        }

    def metrics(self, run_id: str) -> dict[str, Any]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT entity_id, event_type, payload_json FROM events WHERE run_id=? ORDER BY sequence",
                (run_id,),
            ).fetchall()
        counts: dict[str, int] = {}
        per_entity: dict[str, dict[str, Any]] = {}
        action_results = 0
        successful_actions = 0
        self_model_reports = 0
        for row in rows:
            event_type = str(row["event_type"])
            counts[event_type] = counts.get(event_type, 0) + 1
            payload = json.loads(row["payload_json"])
            entity_id = row["entity_id"]
            if entity_id:
                entity = per_entity.setdefault(
                    str(entity_id),
                    {"decisions": 0, "model_errors": 0, "denied_actions": 0, "tokens_used": 0},
                )
                if event_type == "decision":
                    entity["decisions"] += 1
                    entity["tokens_used"] = int(payload.get("tokens_used", entity["tokens_used"]))
                    if payload.get("self_model_summary"):
                        self_model_reports += 1
                elif event_type == "model_error":
                    entity["model_errors"] += 1
                elif event_type == "action_denied":
                    entity["denied_actions"] += 1
            if event_type == "action_result":
                action_results += 1
                successful_actions += int(bool(payload.get("success")))
        return {
            "event_counts": counts,
            "per_entity": per_entity,
            "action_results": action_results,
            "successful_actions": successful_actions,
            "action_success_rate": round(successful_actions / action_results, 4) if action_results else None,
            "self_model_reports": self_model_reports,
        }

    def verify(self, run_id: str) -> bool:
        previous = "GENESIS"
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM events WHERE run_id=? ORDER BY sequence",
                (run_id,),
            ).fetchall()
        for row in rows:
            event = {
                "event_id": row["event_id"],
                "run_id": row["run_id"],
                "tick": row["tick"],
                "entity_id": row["entity_id"],
                "event_type": row["event_type"],
                "payload": json.loads(row["payload_json"]),
                "previous_hash": row["previous_hash"],
                "created_at": row["created_at"],
            }
            if row["previous_hash"] != previous or row["event_hash"] != self._digest(event):
                return False
            previous = row["event_hash"]
        return True

    def write_frame(self, entity_id: str, data: bytes) -> Path:
        path = self.frames_dir / f"{entity_id}.jpg"
        temporary = path.with_suffix(".jpg.tmp")
        temporary.write_bytes(data)
        temporary.replace(path)
        return path

    def read_control(self) -> str:
        if not self.control_path.exists():
            return "run"
        try:
            value = json.loads(self.control_path.read_text(encoding="utf-8"))
            return str(value.get("command", "run"))
        except (OSError, json.JSONDecodeError):
            return "run"

    def write_control(self, command: str) -> None:
        temporary = self.control_path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"command": command, "updated_at": utc_now()}), encoding="utf-8")
        temporary.replace(self.control_path)
