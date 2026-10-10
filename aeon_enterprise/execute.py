"""Run one job without inheriting control-plane credentials."""

from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
from aeon_worker.models import ActionGrant, TaskSpec
from aeon_worker.runner import TaskRunner, TaskStore
from codebee_improve.storage import atomic_write_json


def execute(job: dict, root: Path, *, adapter=None) -> dict:
    if not re.fullmatch(r"job_[a-f0-9]{32}", job["id"]):
        raise ValueError("Invalid control-plane job ID")
    root = root.resolve()
    workspace = root / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    task_id = "task-" + job["id"][4:]
    store = TaskStore(root / "state")
    runner = TaskRunner(store, adapter)
    if (store.directory(task_id) / "checkpoint.json").exists():
        checkpoint = store.load(task_id)
        options = {}
        if job.get("resume_options") and checkpoint["status"] not in {"completed", "failed"}:
            # The queue holds cumulative authorized ceilings. A claim may replay
            # after an extension was saved but before its result was delivered.
            # Reconcile ceilings rather than applying the same relative grant twice.
            fields = {
                "additional_model_tokens": ("max_tokens", "max_model_tokens"),
                "additional_steps": ("max_steps", "max_steps"),
                "additional_minutes": ("deadline_minutes", "deadline_minutes"),
                "additional_revisions": ("max_revisions", "max_revisions"),
            }
            for option, (queue_field, spec_field) in fields.items():
                delta = job[queue_field] - checkpoint["spec"][spec_field]
                if delta < 0:
                    raise ValueError("Checkpoint limits exceed the authorized queue ceilings")
                options[option] = delta
        result = runner.resume(task_id, **options)
    else:
        spec = TaskSpec(
            brief=job["brief"],
            workspace=str(workspace),
            task_id=task_id,
            grant=ActionGrant.from_dict(job["grant"]),
            deadline_minutes=job["deadline_minutes"],
            max_model_tokens=job["max_tokens"],
            max_steps=job["max_steps"],
            max_revisions=job["max_revisions"],
        )
        result = runner.start(spec)
    atomic_write_json(root / "runtime-result.json", result)
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--job-root", type=Path, required=True)
    a = p.parse_args()
    job = json.loads((a.job_root / "job.json").read_text(encoding="utf-8"))
    execute(job, a.job_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
