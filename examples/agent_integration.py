"""Executable SDK example. Replace deterministic callback with your agent model.

Run: python examples/agent_integration.py --workspace ./aeon-output
This proves the integration contract, not model intelligence.
"""

import argparse
from pathlib import Path

from aeon_worker import AEONWorker
from aeon_worker.demo import SMOKE_BRIEF, create_adapter


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--task-root", type=Path)
    args = parser.parse_args()
    worker = AEONWorker(adapter=create_adapter(), task_root=args.task_root)
    result = worker.run(SMOKE_BRIEF, args.workspace)
    print(f"{result['status']}: {result['artifacts']} (audit: {result['audit_valid']})")
    if result["status"] != "completed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
