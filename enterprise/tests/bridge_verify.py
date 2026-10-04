"""Full local HTTP-to-worker-to-artifact fixture, without model/network credentials."""

import hashlib
import json
from pathlib import Path
import tempfile
import urllib.request
import urllib.error
import uuid

from aeon_enterprise.execute import execute
from aeon_enterprise.worker import Client, deliver
from aeon_worker.demo import create_adapter, SMOKE_BRIEF

ORIGIN = "http://127.0.0.1:8787"


def call(path, method="GET", data=None, extra=None):
    headers = {"Origin": ORIGIN, "Content-Type": "application/json", **(extra or {})}
    payload = json.dumps(data).encode() if data is not None else None
    with urllib.request.urlopen(
        urllib.request.Request(
            ORIGIN + "/api" + path, data=payload, method=method, headers=headers
        ),
        timeout=20,
    ) as response:
        return json.load(response)


def main():
    call("/session")
    # Remove unfinished UI fixture jobs so this test only claims its own assignment.
    for j in call("/orgs/org_primary/jobs")["jobs"]:
        if j["status"] in {"queued", "running"} and (j["title"].startswith("UI acceptance") or j["title"] == "Deterministic integration fixture"):
            call(f"/orgs/org_primary/jobs/{j['id']}/cancel", "POST", {})
    enrollment = call(
        "/orgs/org_primary/workers",
        "POST",
        {"name": "Local integration fixture", "mode": "trusted-local"},
    )
    client = Client(enrollment["connection"], allow_local=True)
    job = call(
        "/orgs/org_primary/jobs",
        "POST",
        {
            "title": "Deterministic integration fixture",
            "brief": SMOKE_BRIEF,
            "max_tokens": 50000,
        },
        {"Idempotency-Key": str(uuid.uuid4())},
    )["job"]
    claim = client.request("/api/worker/claim", data={})
    assert claim["job"]["id"] == job["id"]
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        result = execute(claim["job"], root, adapter=create_adapter())
        assert result["status"] == "completed", result
        try:
            deliver(client, claim["job"], claim["lease_token"], root, result)
        except urllib.error.HTTPError as error:
            print(error.read().decode())
            raise
    final = call(f"/orgs/org_primary/jobs/{job['id']}")
    assert final["job"]["status"] == "completed"
    for artifact in final["artifacts"]:
        with urllib.request.urlopen(
            ORIGIN + "/api/orgs/org_primary/artifacts/" + artifact["id"], timeout=20
        ) as response:
            assert hashlib.sha256(response.read()).hexdigest() == artifact["sha256"]
    output = {
        "environment": "local SQLite/R2 harness",
        "model": "deterministic-no-model",
        "job_status": "completed",
        "artifact_count": len(final["artifacts"]),
        "artifact_hashes_verified": True,
        "runtime_audit_valid": final["job"]["result"]["audit_valid"],
    }
    out = Path(__file__).resolve().parents[2] / "artifacts/enterprise-0.4.0/bridge-check.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, indent=2))
    print(json.dumps(output))


if __name__ == "__main__":
    main()
