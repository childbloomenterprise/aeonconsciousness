from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from pathlib import Path

from .backends import Ai2ThorBackend
from .dashboard import serve_dashboard
from .ledger import EventLedger, default_runtime_root
from .preservation import PreservationRunner, render_preservation_report
from .runner import WorldRunner, load_config


def _load_env(path: Path | None) -> None:
    if path is None or not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def doctor(config_path: Path | None = None) -> int:
    supported, reason = Ai2ThorBackend.runtime_support()
    try:
        import ai2thor

        ai2thor_version = getattr(ai2thor, "__version__", "installed")
        import_ok = True
    except Exception as error:
        ai2thor_version = str(error)
        import_ok = False

    report: dict[str, object] = {
        "python": sys.version.split()[0],
        "os": platform.platform(),
        "ai2thor_import": import_ok,
        "ai2thor_version": ai2thor_version,
        "native_ai2thor_runtime": supported,
        "runtime_note": reason,
        "runtime_root": str(default_runtime_root()),
    }
    if config_path:
        config = load_config(config_path)
        report["credentials"] = {
            entity["entity_id"]: {
                "environment_variable": entity.get("api_key_env", "NVIDIA_API_KEY"),
                "present": bool(os.environ.get(entity.get("api_key_env", "NVIDIA_API_KEY"))),
            }
            for entity in config.get("entities", [])
            if entity.get("provider") in {"nvidia", "openai_compatible"} and entity.get("api_key_env")
        }
    print(json.dumps(report, indent=2))
    return 0 if import_ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aeon-world", description="AEON multi-entity AI2-THOR runtime")
    parser.add_argument("--env-file", type=Path, default=None, help="Optional local environment file")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subparsers.add_parser("doctor", help="Check runtime and credentials")
    doctor_parser.add_argument("--config", type=Path)

    run_parser = subparsers.add_parser("run", help="Run world simulation")
    run_parser.add_argument("--config", type=Path, required=True)
    run_parser.add_argument("--backend", choices=["fake", "ai2thor"])
    run_parser.add_argument("--ticks", type=int)
    run_parser.add_argument("--run-dir", type=Path)

    monitor_parser = subparsers.add_parser("monitor", help="Serve local live monitor")
    monitor_parser.add_argument("--run-dir", type=Path, required=True)
    monitor_parser.add_argument("--host", default="127.0.0.1")
    monitor_parser.add_argument("--port", type=int, default=8765)

    verify_parser = subparsers.add_parser("verify", help="Verify event hash chain")
    verify_parser.add_argument("--run-dir", type=Path, required=True)

    report_parser = subparsers.add_parser("report", help="Print monitoring metrics as JSON")
    report_parser.add_argument("--run-dir", type=Path, required=True)

    preserve_parser = subparsers.add_parser("preserve", help="Run the controlled preservation pilot")
    preserve_parser.add_argument("--config", type=Path, required=True)
    preserve_parser.add_argument("--run-dir", type=Path)

    preservation_report_parser = subparsers.add_parser(
        "preserve-report", help="Render technical, child-friendly, or JSON preservation results"
    )
    preservation_report_parser.add_argument("--run-dir", type=Path, required=True)
    preservation_report_parser.add_argument(
        "--format", choices=["technical", "child", "json"], default="technical"
    )

    args = parser.parse_args(argv)
    _load_env(args.env_file)

    if args.command == "doctor":
        return doctor(args.config)
    if args.command == "run":
        config = load_config(args.config)
        if args.backend:
            config.setdefault("run", {})["backend"] = args.backend
        if args.ticks is not None:
            config.setdefault("run", {})["ticks"] = args.ticks
        try:
            result = WorldRunner(config, run_dir=args.run_dir).run()
        except Exception as error:
            print(json.dumps({"status": "failed", "error": str(error)}, indent=2), file=sys.stderr)
            return 1
        print(json.dumps(result, indent=2))
        return 0 if result["status"] in {"completed", "stopped"} else 1
    if args.command == "monitor":
        serve_dashboard(args.run_dir, args.host, args.port)
        return 0
    if args.command == "verify":
        ledger = EventLedger(args.run_dir)
        run = ledger.latest_run()
        valid = bool(run and ledger.verify(run["run_id"]))
        print(json.dumps({"run_id": run["run_id"] if run else None, "valid": valid}))
        return 0 if valid else 1
    if args.command == "report":
        ledger = EventLedger(args.run_dir)
        run = ledger.latest_run()
        payload = {
            "run": run,
            "metrics": ledger.metrics(run["run_id"]) if run else {},
            "audit_valid": bool(run and ledger.verify(run["run_id"])),
        }
        print(json.dumps(payload, indent=2))
        return 0 if run else 1
    if args.command == "preserve":
        config = load_config(args.config)
        try:
            result = PreservationRunner(config, run_dir=args.run_dir).run()
        except Exception as error:
            print(json.dumps({"status": "failed", "error": str(error)}, indent=2), file=sys.stderr)
            return 1
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "completed" else 1
    if args.command == "preserve-report":
        try:
            print(render_preservation_report(args.run_dir, args.format))
        except Exception as error:
            print(json.dumps({"status": "failed", "error": str(error)}, indent=2), file=sys.stderr)
            return 1
        return 0
    return 2
