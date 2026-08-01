from __future__ import annotations

import re
from datetime import UTC, datetime

from aeon.core.contracts import MemoryRecord
from aeon.storage.base import Storage


class Citta:
    def __init__(self, storage: Storage) -> None:
        self.storage = storage

    @staticmethod
    def _terms(text: str) -> set[str]:
        return {word.lower() for word in re.findall(r"[A-Za-z0-9_-]{3,}", text)}

    def retrieve(self, query: str, limit: int = 5) -> list[tuple[MemoryRecord, float]]:
        query_terms = self._terms(query)
        scored = []
        for memory in self.storage.list_memories():
            terms = self._terms(memory.content)
            score = len(query_terms & terms) / max(1, len(query_terms | terms))
            if score > 0:
                scored.append((memory, round(score, 4)))
        return sorted(scored, key=lambda item: (-item[1], item[0].memory_id))[:limit]

    def remember(
        self,
        content: str,
        memory_type: str,
        source: str,
        provenance: list[str],
        confidence: float = 0.7,
    ) -> MemoryRecord:
        memory = MemoryRecord(
            memory_type=memory_type,
            content=content,
            source=source,
            provenance=provenance,
            confidence=confidence,
        )
        self.storage.save_memory(memory)
        return memory

    def revise(self, memory_id: str, content: str, reason: str) -> MemoryRecord:
        current = next(
            memory for memory in self.storage.list_memories() if memory.memory_id == memory_id
        )
        current.revision_history.append(
            {
                "content": current.content,
                "revised_at": current.revised_at.isoformat(),
                "reason": reason,
            }
        )
        current.content = content
        current.revised_at = datetime.now(UTC)
        self.storage.save_memory(current)
        return current
