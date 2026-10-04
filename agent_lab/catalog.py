from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CATALOG_PATH = Path(__file__).with_name("catalog.json")


def load_catalog(path: Path = CATALOG_PATH) -> tuple[dict[str, Any], ...]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Agent catalog must be a list.")
    identifiers: set[str] = set()
    entries: list[dict[str, Any]] = []
    for raw in payload:
        if not isinstance(raw, dict):
            raise ValueError("Every catalog entry must be an object.")
        entry = dict(raw)
        identifier = str(entry.get("id", "")).strip()
        if not identifier or identifier in identifiers:
            raise ValueError(f"Agent catalog contains an empty or duplicate id: {identifier}")
        identifiers.add(identifier)
        if not str(entry.get("source", "")).startswith("https://github.com/"):
            raise ValueError(f"Catalog source must be an official GitHub repository: {identifier}")
        entries.append(entry)
    return tuple(entries)
