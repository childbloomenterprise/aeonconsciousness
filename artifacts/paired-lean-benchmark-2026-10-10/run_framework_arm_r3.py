"""Round-3 complex-brief framework arm: submit 3 authorized complex paired-benchmark jobs and poll them.

Usage:
  python run_framework_arm_r3.py submit
  python run_framework_arm_r3.py poll
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "briefs-complex-round3.json").read_text(encoding="utf-8"))
ORIGIN = "http://127.0.0.1:8787"
KEY_PREFIX = "aeon-20261010-complex-paired-v1-"
# Infra-outage retry for the job the server restart killed mid-execute; brief unchanged.
RETRY_SUFFIX = {"complex-user-intent-truncated": "-retry1"}


def stamp():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def call(path, data=None, key=None):
    headers = {"Origin": ORIGIN, "Content-Type": "application/json"}
    if key:
        headers["Idempotency-Key"] = key
    request = urllib.request.Request(ORIGIN + "/api" + path, headers=headers,
        data=json.dumps(data).encode() if data is not None else None)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def task_request(task):
    return {
        "title": task["title"],
        "kind": task["kind"],
        "brief": task["brief"],
        "max_tokens": task["max_tokens"],
        "max_steps": task["max_steps"],
        "max_revisions": 1,
        "deadline_minutes": task["deadline_minutes"],
        "grant": {},
    }


def submit():
    for task in CONFIG["tasks"]:
        folder = ROOT / task["id"]
        marker = folder / "submission.json"
        key = KEY_PREFIX + task["id"] + RETRY_SUFFIX.get(task["id"], "")
        if marker.exists():
            stored = json.loads(marker.read_text(encoding="utf-8"))
            if stored["idempotency_key"] != key or stored["request"] != task_request(task):
                raise ValueError("Saved submission differs from authorized request: " + task["id"])
            job_id = stored["job_id"]
        else:
            response = call("/orgs/org_primary/jobs", task_request(task), key)
            job_id = response["job"]["id"]
            stored = {"submitted_at": stamp(), "idempotency_key": key,
                      "request": task_request(task), "response": {"job": {"id": job_id}}, "job_id": job_id}
            save(marker, stored)
        print(json.dumps({"task": task["id"], "job_id": job_id}))


def fetch_job(job_id):
    return call("/orgs/org_primary/jobs/" + job_id)


def inspect(download=True):
    for task in CONFIG["tasks"]:
        folder = ROOT / task["id"]
        submitted = json.loads((folder / "submission.json").read_text(encoding="utf-8"))
        record = fetch_job(submitted["job_id"])
        save(folder / "control-plane-result.json", {"inspected_at": stamp(), **record})
        job = record["job"]
        checks = []
        if download:
            import hashlib
            for artifact in record.get("artifacts", []):
                relative = PurePosixPath(artifact["path"])
                if relative.is_absolute() or any(p in {"", ".", ".."} for p in relative.parts):
                    raise ValueError("Artifact path escapes evidence directory")
                with urllib.request.urlopen(ORIGIN + "/api/orgs/org_primary/artifacts/" + artifact["id"], timeout=30) as response:
                    raw = response.read(8_000_001)
                    attachment = response.headers.get("Content-Disposition", "")
                digest = hashlib.sha256(raw).hexdigest()
                if len(raw) != artifact["size"] or digest != artifact["sha256"] or "attachment" not in attachment:
                    raise ValueError("Artifact integrity check failed: " + artifact["path"])
                dest = folder / "downloads" / Path(*relative.parts)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(raw)
                checks.append({"path": artifact["path"], "size": len(raw), "sha256": digest})
            save(folder / "download-checks.json", {"checked_at": stamp(), "job_id": job["id"], "artifacts": checks})
        result = job.get("result") or {}
        print(json.dumps({"task": task["id"], "status": job["status"], "used_tokens": job.get("used_tokens"),
                          "progress": job.get("progress"), "reason": result.get("reason"),
                          "artifact_count": len(record.get("artifacts", [])), "verified_downloads": len(checks)}))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "poll"
    if mode == "submit":
        submit()
    else:
        inspect(download=True)
