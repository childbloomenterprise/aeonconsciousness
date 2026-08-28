from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .curator import Curator
from .engine import SelfImprovementEngine


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect Codebee self-improvement state.")
    parser.add_argument("command", choices=("status", "snapshot", "curate", "verify-audit"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--namespace", action="append", dest="namespaces")
    args = parser.parse_args()
    engine = SelfImprovementEngine(args.root)

    if args.command == "verify-audit":
        print("valid" if engine.audit.verify() else "invalid")
        return 0 if engine.audit.verify() else 1
    if args.command == "snapshot":
        print(engine.memory.snapshot(args.namespaces or ["user", "project", "workspace", "agent"]).render())
        return 0
    if args.command == "curate":
        report = Curator(engine).review(dry_run=True)
        print(json.dumps({"dry_run": True, "actions": [asdict(a) for a in report.actions]}, indent=2))
        return 0

    candidates = engine._load()
    payload = {
        "root": str(engine.root),
        "candidates": len(candidates),
        "candidate_states": {
            state: sum(1 for candidate in candidates.values() if candidate.status.value == state)
            for state in sorted({candidate.status.value for candidate in candidates.values()})
        },
        "active_memories": len(engine.memory.list()),
        "active_skills": len(engine.skills.list()),
        "audit_valid": engine.audit.verify(),
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
