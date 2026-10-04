"""Command-line entry point for AEON personal work."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from .models import ActionGrant, TaskSpec, deadline_minutes_from_brief
from .providers import ProviderRouter
from .runner import TaskRunner, TaskStore
from .benchmark import analyze_benchmark, load_cases, run_benchmark
from .blind_review import review_blind_manifest


def _json(value: object) -> None:
    # Windows terminals may still use legacy encodings despite UTF-8 files.
    print(json.dumps(value, indent=2, ensure_ascii=True), flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aeon", description="AEON personal-worker MVP")
    parser.add_argument("--task-root", type=Path, help="Override task checkpoint directory")
    parser.add_argument("--adapter", help="Trusted installed Python module:factory supplying structured agent decisions")
    sub = parser.add_subparsers(dest="command", required=True)
    task = sub.add_parser("task", help="Run or inspect a personal-work task")
    task_sub = task.add_subparsers(dest="task_command", required=True)

    start = task_sub.add_parser("start", help="Run one broad brief to a checked local deliverable")
    brief_group = start.add_mutually_exclusive_group(required=True)
    brief_group.add_argument("--brief-file", type=Path)
    brief_group.add_argument("--brief")
    start.add_argument("--workspace", type=Path, required=True)
    start.add_argument("--grant-file", type=Path, help="Explicit external-action grant JSON")
    start.add_argument("--deadline-minutes", type=int, help="Override deadline parsed from brief (default: 90 minutes)")
    start.add_argument("--max-model-tokens", type=int, default=50_000)
    start.add_argument("--max-steps", type=int, default=32)
    start.add_argument("--max-revisions", type=int, default=3)
    start.add_argument("--result-only", action="store_true", help="Emit one final JSON object for subprocess integrations")

    for name in ("status", "resume", "result"):
        child = task_sub.add_parser(name)
        child.add_argument("task_id")
        if name == "resume":
            child.add_argument("--additional-model-tokens", type=int, default=0)
            child.add_argument("--additional-steps", type=int, default=0)
            child.add_argument("--additional-minutes", type=int, default=0)
            child.add_argument("--additional-revisions", type=int, default=0)

    doctor = sub.add_parser("doctor", help="Inspect credentials and browser dependency")
    doctor.add_argument("--probe", action="store_true", help="Make a tiny model request to verify current provider availability")
    smoke = sub.add_parser("smoke", help="Credential-free deterministic installation check (not an AI benchmark)")
    smoke.add_argument("--workspace", type=Path, required=True)
    benchmark = sub.add_parser("benchmark", help="Run paired direct versus AEON tasks")
    benchmark_sub = benchmark.add_subparsers(dest="benchmark_command", required=True)
    benchmark_run = benchmark_sub.add_parser("run")
    benchmark_run.add_argument("--cases", type=Path, required=True)
    benchmark_run.add_argument("--output", type=Path, required=True)
    benchmark_run.add_argument("--retry-interrupted", action="store_true", help="Rerun both arms of provider-interrupted pairs in a fresh attempt directory")
    benchmark_run.add_argument("--pause-seconds", type=float, default=0.0, help="Wait between newly run arms to respect provider rate limits")
    benchmark_analyze = benchmark_sub.add_parser("analyze")
    benchmark_analyze.add_argument("--run-dir", type=Path, required=True)
    benchmark_analyze.add_argument("--ratings", type=Path, required=True)
    benchmark_analyze.add_argument("--pricing", type=Path, help="Run-date paid list-price JSON for optional cost estimate")
    benchmark_analyze.add_argument("--diagnostic", action="store_true", help="Report descriptive results while excluding invalid pairs; never claim superiority")
    benchmark_review = benchmark_sub.add_parser("review", help="Automated blind artifact grading; explicitly labeled as model review")
    benchmark_review.add_argument("--manifest", type=Path, required=True)
    benchmark_review.add_argument("--output", type=Path, required=True)
    benchmark_review.add_argument("--passes", type=int, default=2)
    args = parser.parse_args(argv)
    if args.command == "benchmark" and args.adapter:
        parser.error("--adapter currently applies to task/doctor commands. Use run_benchmark(provider_factory=...) from Python for paired custom adapters.")
    if args.command == "doctor":
        chromium_installed = False
        try:
            from playwright.sync_api import sync_playwright

            browser_package = True
            with sync_playwright() as playwright:
                chromium_installed = Path(playwright.chromium.executable_path).is_file()
        except ImportError:
            browser_package = False
        diagnostic = {
            "nvidia_key_present": bool(os.environ.get("NVIDIA_API_KEY")),
            "gemini_key_present": bool(os.environ.get("GEMINI_API_KEY")),
            "playwright_package_present": browser_package,
            "chromium_installed": chromium_installed,
            "model_route": "NVIDIA then Gemini",
            "expected_provider": "nvidia" if os.environ.get("NVIDIA_API_KEY") else "gemini" if os.environ.get("GEMINI_API_KEY") else "unavailable",
        }
        diagnostic["codex_executable_present"] = bool(os.environ.get("AEON_CODEX_BINARY") or shutil.which("codex"))
        if os.environ.get("AEON_MODEL_BACKEND") == "codex":
            diagnostic.update({"model_route": "Codex opt-in structured inference", "expected_provider": "codex"})
        if args.adapter:
            diagnostic.update({"model_route": "Operator-supplied adapter", "expected_provider": "custom", "adapter": args.adapter})
        if args.probe:
            try:
                from .sdk import load_adapter
                provider = load_adapter(args.adapter) if args.adapter else ProviderRouter()
                reply = provider.complete("Return a JSON object with ready set to true.", {"ready": True}, max_output_tokens=128)
                diagnostic["probe"] = {"available": True, "provider": reply.provider, "model": reply.model}
            except Exception as error:
                diagnostic["probe"] = {"available": False, "error": f"{type(error).__name__}: {error}"[:200]}
        _json(diagnostic)
        return 0 if not args.probe or diagnostic["probe"]["available"] else 1
    if args.command == "benchmark":
        try:
            if args.benchmark_command == "run":
                _json(run_benchmark(load_cases(args.cases), args.output, retry_interrupted=args.retry_interrupted, pause_seconds=args.pause_seconds))
            elif args.benchmark_command == "review":
                _json(review_blind_manifest(args.manifest, args.output, passes=args.passes))
            else:
                _json(analyze_benchmark(args.run_dir, args.ratings, args.pricing, diagnostic=args.diagnostic))
            return 0
        except (OSError, ValueError, RuntimeError) as error:
            _json({"status": "failed", "error": f"{type(error).__name__}: {error}"})
            return 2
    store = TaskStore(args.task_root)
    try:
        from .sdk import load_adapter
        if args.command == "smoke":
            from .demo import SMOKE_BRIEF, create_adapter
            result = TaskRunner(store, create_adapter()).start(TaskSpec(SMOKE_BRIEF, str(args.workspace)))
            _json({**result, "smoke_test": "deterministic; no model invoked"})
            return 0 if result["status"] == "completed" and result["audit_valid"] else 1
        runner = TaskRunner(store, load_adapter(args.adapter) if args.adapter else None)
        if args.task_command == "start":
            brief = args.brief if args.brief is not None else args.brief_file.read_text(encoding="utf-8")
            grant = ActionGrant.from_dict(json.loads(args.grant_file.read_text(encoding="utf-8")) if args.grant_file else None)
            spec = TaskSpec(
                brief=brief, workspace=str(args.workspace), grant=grant,
                deadline_minutes=args.deadline_minutes if args.deadline_minutes is not None else (deadline_minutes_from_brief(brief) or 90),
                max_model_tokens=args.max_model_tokens,
                max_steps=args.max_steps,
                max_revisions=args.max_revisions,
            )
            if not args.result_only:
                _json({"task_id": spec.task_id, "status": "starting", "workspace": spec.workspace})
            result = runner.start(spec)
            _json(result)
            return 0 if result["status"] == "completed" else 1
        if args.task_command == "resume":
            result = runner.resume(
                args.task_id,
                additional_model_tokens=args.additional_model_tokens,
                additional_steps=args.additional_steps,
                additional_minutes=args.additional_minutes,
                additional_revisions=args.additional_revisions,
            )
            _json(result)
            return 0 if result["status"] == "completed" else 1
        if args.task_command == "result":
            _json(store.result(args.task_id))
            return 0
        state = store.load(args.task_id)
        _json({
            "task_id": args.task_id,
            "status": state["status"],
            "phase": state["phase"],
            "steps": state["steps"],
            "revisions": state["revisions"],
            "artifacts": state["artifacts"],
            "tokens": state["tokens"],
            "deadline_at": state["deadline_at"],
            "provider_route": state["provider_route"],
        })
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        _json({"status": "failed", "error": f"{type(error).__name__}: {error}"})
        return 2


if __name__ == "__main__":
    sys.exit(main())
