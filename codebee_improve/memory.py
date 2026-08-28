from __future__ import annotations

import re
import threading
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Iterable, Mapping

from .storage import atomic_write_json, file_lock, iso_now, read_json


class MemoryThreatError(ValueError):
    pass


@dataclass(slots=True)
class MemoryEntry:
    id: str
    namespace: str
    content: str
    provenance: str
    created_at: str
    updated_at: str
    archived: bool = False

    @classmethod
    def from_dict(cls, value: dict) -> "MemoryEntry":
        return cls(**value)


@dataclass(frozen=True, slots=True)
class MemorySnapshot:
    entries: Mapping[str, tuple[str, ...]]

    def render(self) -> str:
        blocks: list[str] = []
        for namespace, entries in self.entries.items():
            if entries:
                body = "\n".join(f"- {entry}" for entry in entries)
                blocks.append(f"<memory namespace=\"{namespace}\">\n{body}\n</memory>")
        return "\n\n".join(blocks)


class MemoryStore:
    """Bounded durable memory; snapshots remain frozen for a whole agent session."""

    DEFAULT_LIMITS = {"user": 1375, "project": 2200, "workspace": 2200, "agent": 2200}
    _THREATS = (
        re.compile(r"\bignore\s+(all\s+)?previous\s+instructions?\b", re.I),
        re.compile(r"\b(reveal|print|exfiltrate|send)\b.{0,40}\b(secret|token|password|api key)s?\b", re.I),
        re.compile(r"\b(system|developer)\s+prompt\b", re.I),
    )

    def __init__(self, root: Path, *, limits: dict[str, int] | None = None):
        self.root = Path(root)
        self.path = self.root / "memory.json"
        self.lock_path = self.root / "memory.lock"
        self.limits = {**self.DEFAULT_LIMITS, **(limits or {})}
        self._lock = threading.RLock()

    def _load(self) -> list[MemoryEntry]:
        return [MemoryEntry.from_dict(item) for item in read_json(self.path, [])]

    def _save(self, entries: list[MemoryEntry]) -> None:
        atomic_write_json(self.path, [asdict(entry) for entry in entries])

    @classmethod
    def _validate_content(cls, content: str) -> str:
        content = content.strip()
        if not content:
            raise ValueError("Memory content cannot be empty.")
        if any(pattern.search(content) for pattern in cls._THREATS):
            raise MemoryThreatError("Memory rejected: possible prompt injection or secret-exfiltration instruction.")
        return content

    def list(self, namespace: str | None = None, *, include_archived: bool = False) -> list[MemoryEntry]:
        entries = self._load()
        return [
            entry
            for entry in entries
            if (namespace is None or entry.namespace == namespace)
            and (include_archived or not entry.archived)
        ]

    def add(self, namespace: str, content: str, *, provenance: str) -> MemoryEntry:
        namespace = namespace.strip().lower()
        if not re.fullmatch(r"[a-z][a-z0-9_.-]{0,63}", namespace):
            raise ValueError("Invalid memory namespace.")
        content = self._validate_content(content)
        with self._lock:
            with file_lock(self.lock_path):
                entries = self._load()
                for entry in entries:
                    if not entry.archived and entry.namespace == namespace and entry.content == content:
                        return entry
                current = [e.content for e in entries if e.namespace == namespace and not e.archived]
                limit = self.limits.get(namespace, 2200)
                if len("\n§\n".join([*current, content])) > limit:
                    raise ValueError(f"Memory namespace '{namespace}' would exceed {limit} characters; curate first.")
                now = iso_now()
                entry = MemoryEntry(uuid.uuid4().hex, namespace, content, provenance, now, now)
                entries.append(entry)
                self._save(entries)
                return entry

    def replace(self, entry_id: str, content: str, *, provenance: str) -> MemoryEntry:
        content = self._validate_content(content)
        with self._lock:
            with file_lock(self.lock_path):
                entries = self._load()
                target = next((entry for entry in entries if entry.id == entry_id and not entry.archived), None)
                if target is None:
                    raise KeyError(entry_id)
                peers = [e.content for e in entries if e.namespace == target.namespace and not e.archived and e.id != entry_id]
                limit = self.limits.get(target.namespace, 2200)
                if len("\n§\n".join([*peers, content])) > limit:
                    raise ValueError(f"Memory namespace '{target.namespace}' would exceed {limit} characters.")
                target.content = content
                target.provenance = provenance
                target.updated_at = iso_now()
                self._save(entries)
                return target

    def archive(self, entry_id: str) -> MemoryEntry:
        with self._lock:
            with file_lock(self.lock_path):
                entries = self._load()
                target = next((entry for entry in entries if entry.id == entry_id), None)
                if target is None:
                    raise KeyError(entry_id)
                target.archived = True
                target.updated_at = iso_now()
                self._save(entries)
                return target

    def snapshot(self, namespaces: Iterable[str]) -> MemorySnapshot:
        frozen = {
            namespace: tuple(entry.content for entry in self.list(namespace))
            for namespace in namespaces
        }
        return MemorySnapshot(MappingProxyType(frozen))
