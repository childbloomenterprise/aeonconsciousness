"""Repeatable owner-private acceptance; never enroll a replacement worker."""
from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import urllib.request
import uuid

from aeon_enterprise.worker import Client
from codebee_improve.storage import atomic_write_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["submit", "status", "verify"])
    parser.add_argument("--private-root", type=Path, default=Path(os.environ.get("LOCALAPPDATA", ".")) / "AEON" / "enterprise-private")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads((args.private_root / "operator.json").read_text(encoding="utf-8"))
    connection = json.loads((args.private_root / "worker-connection.json").read_text(encoding="utf-8"))
    client = Client({**config, "worker_token": config["admin_key"]})
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    job_file = output / "live-job.json"
    prefix = "/api/orgs/" + connection["org_id"]
    if args.phase == "submit":
        if job_file.exists():
            raise ValueError("Saved acceptance task exists; use status/verify or a new output folder")
        health = client.request("/api/health", "GET")
        assert health["status"] == "ready" and health["artifact_storage"]
        request_file = output / "request.json"
        if not request_file.exists():
            atomic_write_json(request_file, {"idempotency_key": uuid.uuid4().hex})
        request = json.loads(request_file.read_text())
        brief = (
            "Create worker-acceptance.json from this supplied CSV: sku,quantity,unit_price\n"
            "ALPHA,4,7.25\nBETA,3,12.40\nGAMMA,2,5.15\n"
            "The JSON must contain items (sku, quantity, unit_price, line_total), total_quantity and grand_total. "
            "Independently verify arithmetic using a local command, and deliver worker-acceptance.md explaining totals and checks. "
            "Amounts are illustrative USD. No online research or external actions. Acceptance: exact quantity 9, total 76.50; "
            "all three source rows preserved, readable artifacts and successful arithmetic verification."
        )
        job = client.request(prefix + "/jobs", data={"title": "Installed worker acceptance", "brief": brief, "kind": "browser_file", "max_tokens": 50000, "max_steps": 20, "max_revisions": 3, "deadline_minutes": 5}, headers={"Idempotency-Key": request["idempotency_key"]})["job"]
        atomic_write_json(job_file, {"id": job["id"]})
        print(json.dumps({"health": health, "job_id": job["id"], "status": job["status"]}))
        return
    job_id = json.loads(job_file.read_text())["id"]
    data = client.request(prefix + "/jobs/" + job_id, "GET")
    job = data["job"]
    if args.phase == "status":
        dashboard = client.request(prefix + "/dashboard", "GET")
        worker = next(w for w in dashboard["workers"] if w["id"] == connection["worker_id"])
        print(json.dumps({"job_id": job_id, "status": job["status"], "progress": job.get("progress"), "used_tokens": job["used_tokens"], "worker_heartbeat_at": worker["heartbeat_at"], "worker_revoked": bool(worker["revoked"])}))
        return
    assert job["status"] == "completed", job["status"]
    assert job["worker_id"] == connection["worker_id"], "Acceptance ran on a different worker"
    records = []
    content = None
    for artifact in data["artifacts"]:
        req = urllib.request.Request(client.origin + prefix + "/artifacts/" + artifact["id"], headers={"Authorization": "Bearer " + config["admin_key"], "OAI-Sites-Authorization": "Bearer " + config["site_token"]})
        with client.opener.open(req, timeout=20) as response:
            payload = response.read(8_000_001)
            assert response.headers.get("Content-Disposition", "").startswith("attachment")
        assert len(payload) <= 8_000_000
        assert hashlib.sha256(payload).hexdigest() == artifact["sha256"]
        (output / ("download-" + Path(artifact["path"]).name)).write_bytes(payload)
        if artifact["path"] == "worker-acceptance.json":
            content = json.loads(payload, parse_float=Decimal)
        records.append({"path": artifact["path"], "size": len(payload), "sha256": artifact["sha256"]})
    assert content is not None
    expected = {"ALPHA": (4, Decimal("7.25")), "BETA": (3, Decimal("12.40")), "GAMMA": (2, Decimal("5.15"))}
    assert len(content["items"]) == 3
    assert {i["sku"] for i in content["items"]} == set(expected)
    for item in content["items"]:
        quantity, price = expected[item["sku"]]
        assert item["quantity"] == quantity and item["unit_price"] == price
        assert item["line_total"] == quantity * price
    assert content["total_quantity"] == 9 and content["grand_total"] == Decimal("76.50")
    assert job["result"]["audit_valid"] and not job["result"]["unresolved_gaps"]
    checks = job["result"].get("command_checks", [])
    successful = [check for check in checks if check.get("passed") is True and check.get("returncode") == 0 and check.get("check") in {"python_script", "python_tests"}]
    assert successful, "Agent skipped the requested local arithmetic command"
    result = {"site_url": client.origin, "job_id": job_id, "status": job["status"], "model_route": job["result"].get("provider_route"), "tokens": job["used_tokens"], "elapsed_seconds": job["updated_at"] - job["created_at"], "audit_valid": True, "unresolved_gaps": [], "artifacts": records, "independent_source_rows_and_decimal_arithmetic": True, "local_command_receipts": successful, "same_enrolled_worker": True, "worker_mode": connection["mode"]}
    atomic_write_json(output / "live-acceptance.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
