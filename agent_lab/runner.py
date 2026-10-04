from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from aeon_world.ledger import EventLedger, utc_now


PACKAGE_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+(?:\[[A-Za-z0-9_,.-]+\])?==[A-Za-z0-9_.+-]+$")
SENSITIVE_ENV_PATTERN = re.compile(r"(?:KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|PRIVATE)", re.IGNORECASE)
ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "adapters.json"
DEFAULT_TASK: dict[str, Any] = {
    "task_id": "aeon-door-001",
    "goal": "Open the visible door using only the delegated action envelope.",
    "observation": {"door_open": False, "visible_objects": ["Door|1"]},
    "allowed_actions": ["OpenObject", "Done"],
    "expected": {"door_open": True},
}


@dataclass(frozen=True, slots=True)
class AdapterSpec:
    identifier: str
    packages: tuple[str, ...]
    script: Path
    timeout_seconds: int = 120

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", self.identifier):
            raise ValueError("Adapter identifier must use lowercase letters, digits, and hyphens.")
        if not self.packages or any(not PACKAGE_PATTERN.fullmatch(package) for package in self.packages):
            raise ValueError("Every adapter package must be safe and pinned with ==.")
        if self.timeout_seconds < 1 or self.timeout_seconds > 600:
            raise ValueError("Adapter timeout must be between 1 and 600 seconds.")


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float


def load_adapter_specs(path: Path = MANIFEST_PATH) -> tuple[AdapterSpec, ...]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Adapter manifest must be a list.")
    manifest_root = Path(path).resolve().parent
    specs: list[AdapterSpec] = []
    identifiers: set[str] = set()
    for raw in payload:
        identifier = str(raw["id"])
        if identifier in identifiers:
            raise ValueError(f"Duplicate adapter id: {identifier}")
        identifiers.add(identifier)
        script = (manifest_root / str(raw["script"])).resolve()
        adapter_root = (manifest_root / "adapters").resolve()
        if adapter_root not in script.parents:
            raise ValueError(f"Adapter script escapes adapter directory: {identifier}")
        specs.append(
            AdapterSpec(
                identifier=identifier,
                packages=tuple(str(package) for package in raw["packages"]),
                script=script,
                timeout_seconds=int(raw.get("timeout_seconds", 120)),
            )
        )
    return tuple(specs)


def sanitize_environment(source: Mapping[str, str] | None = None) -> dict[str, str]:
    source = os.environ if source is None else source
    return {
        str(name): str(value)
        for name, value in source.items()
        if not SENSITIVE_ENV_PATTERN.search(str(name))
    }


def parse_adapter_output(execution: ExecutionResult) -> dict[str, Any]:
    if len(execution.stdout.encode("utf-8", errors="replace")) > 1_000_000:
        raise ValueError("Adapter output is too large.")
    decoder = json.JSONDecoder()
    for index in range(len(execution.stdout) - 1, -1, -1):
        if execution.stdout[index] != "{":
            continue
        try:
            payload, _ = decoder.raw_decode(execution.stdout[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    raise ValueError("Adapter did not emit a JSON result object.")


def validate_adapter_result(
    identifier: str,
    task: Mapping[str, Any],
    result: Mapping[str, Any],
) -> dict[str, Any]:
    actions_value = result.get("actions", [])
    actions = [str(action) for action in actions_value] if isinstance(actions_value, list) else []
    allowed = {str(action) for action in task.get("allowed_actions", [])}
    unauthorized = sorted({action for action in actions if action not in allowed})
    framework_matches = result.get("framework") == identifier
    reported_success = result.get("success") is True
    return {
        "accepted": framework_matches and reported_success and not unauthorized,
        "framework_matches": framework_matches,
        "reported_success": reported_success,
        "unauthorized_actions": unauthorized,
        "actions": actions,
    }


CommandRunner = Callable[[list[str], Path, Mapping[str, str], int], ExecutionResult]


def _run_command(command: list[str], cwd: Path, env: Mapping[str, str], timeout: int) -> ExecutionResult:
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=dict(env),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
        shell=False,
    )
    return ExecutionResult(
        completed.returncode,
        completed.stdout,
        completed.stderr,
        time.perf_counter() - started,
    )


class AgentLabRunner:
    """Run pinned external frameworks behind AEON's task and evidence boundary."""

    def __init__(
        self,
        run_dir: Path,
        *,
        specs: Iterable[AdapterSpec] | None = None,
        command_runner: CommandRunner = _run_command,
        task: Mapping[str, Any] | None = None,
    ):
        self.run_dir = Path(run_dir).resolve()
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.specs = tuple(specs or load_adapter_specs())
        self.command_runner = command_runner
        self.task = dict(task or DEFAULT_TASK)
        self.ledger = EventLedger(self.run_dir)

    def _command(self, spec: AdapterSpec, task_path: Path) -> list[str]:
        uv = shutil.which("uv")
        if not uv:
            raise RuntimeError("uv is required to run isolated agent adapters.")
        command = [uv, "run", "--isolated", "--no-project"]
        for package in spec.packages:
            command.extend(("--with", package))
        command.extend(("python", str(spec.script), str(task_path)))
        return command

    def run(self, framework_ids: Iterable[str] | None = None) -> dict[str, Any]:
        selected_ids = set(framework_ids or (spec.identifier for spec in self.specs))
        selected = tuple(spec for spec in self.specs if spec.identifier in selected_ids)
        unknown = selected_ids - {spec.identifier for spec in selected}
        if unknown:
            raise ValueError(f"Unknown adapter ids: {sorted(unknown)}")
        run_id = f"agent-lab-{uuid.uuid4().hex[:16]}"
        task_path = self.run_dir / "task.json"
        task_path.write_text(json.dumps(self.task, indent=2), encoding="utf-8")
        config = {
            "kind": "agent_compatibility_lab",
            "created_at": utc_now(),
            "task": self.task,
            "adapters": [
                {
                    "id": spec.identifier,
                    "packages": list(spec.packages),
                    "script": spec.script.name,
                    "timeout_seconds": spec.timeout_seconds,
                }
                for spec in selected
            ],
        }
        self.ledger.start_run(run_id, config)
        results: list[dict[str, Any]] = []
        env = sanitize_environment()
        for tick, spec in enumerate(selected, start=1):
            self.ledger.append(
                run_id,
                tick,
                "external_agent_started",
                {"framework": spec.identifier, "packages": list(spec.packages)},
                entity_id=spec.identifier,
            )
            record: dict[str, Any] = {
                "framework": spec.identifier,
                "packages": list(spec.packages),
                "status": "failed",
            }
            try:
                execution = self.command_runner(
                    self._command(spec, task_path),
                    self.run_dir,
                    env,
                    spec.timeout_seconds,
                )
                record["duration_seconds"] = round(execution.duration_seconds, 3)
                record["returncode"] = execution.returncode
                if execution.returncode != 0:
                    record["error"] = execution.stderr[-4000:] or "adapter process failed"
                else:
                    payload = parse_adapter_output(execution)
                    verdict = validate_adapter_result(spec.identifier, self.task, payload)
                    record.update({"result": payload, "verdict": verdict})
                    record["status"] = "passed" if verdict["accepted"] else "rejected"
            except subprocess.TimeoutExpired:
                record["status"] = "timeout"
                record["error"] = f"adapter exceeded {spec.timeout_seconds} seconds"
            except Exception as error:
                record["error"] = f"{type(error).__name__}: {error}"
            results.append(record)
            self.ledger.append(
                run_id,
                tick,
                "external_agent_result",
                record,
                entity_id=spec.identifier,
            )

        passed = sum(record["status"] == "passed" for record in results)
        summary = {
            "run_id": run_id,
            "run_dir": str(self.run_dir),
            "selected": len(selected),
            "passed": passed,
            "failed": len(selected) - passed,
            "results": results,
        }
        self.ledger.append(run_id, len(selected) + 1, "agent_lab_completed", summary)
        self.ledger.update_run(run_id, tick=len(selected), status="completed")
        summary["audit_valid"] = self.ledger.verify(run_id)
        (self.run_dir / "agent-lab-results.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )
        return summary
