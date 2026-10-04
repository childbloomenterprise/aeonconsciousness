"""Launch the outbound supervisor using protected, external configuration files."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    root = args.private_root.resolve()
    connection = root / "worker-connection.json"
    config = json.loads(connection.read_text(encoding="utf-8"))
    provider_file = root / "providers.json"
    providers = json.loads(provider_file.read_text()) if provider_file.exists() else {}
    for name in ("NVIDIA_API_KEY", "GEMINI_API_KEY"):
        if providers.get(name):
            os.environ[name] = providers[name]
    from aeon_enterprise.worker import main as worker_main

    sys.argv = [
        "aeon-enterprise-worker",
        "--connection",
        str(connection),
        "--state-root",
        str(root / "jobs"),
    ]
    if config.get("mode") == "trusted-local":
        sys.argv.append("--trusted-local")
    if args.once:
        sys.argv.append("--once")
    return worker_main()


if __name__ == "__main__":
    raise SystemExit(main())
