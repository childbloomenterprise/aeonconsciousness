"""Scoped HTTPS worker with job leases, process isolation, and artifact delivery."""

from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

from agent_lab.runner import sanitize_environment
from codebee_improve.storage import atomic_write_json, file_lock, read_json


class SameOriginRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, origin: str):
        super().__init__()
        self.origin = origin

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urllib.parse.urlsplit(newurl)
        if f"{target.scheme}://{target.netloc}" != self.origin:
            raise PermissionError(
                "Control-plane credential cannot follow cross-origin redirect"
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Client:
    def __init__(self, config: dict, *, allow_local: bool = False):
        parsed = urllib.parse.urlsplit(config["base_url"])
        if (
            parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise ValueError(
                "Use an origin without credentials, path, query, or fragment"
            )
        if parsed.scheme != "https" and not (
            allow_local
            and parsed.scheme == "http"
            and parsed.hostname in {"localhost", "127.0.0.1"}
        ):
            raise ValueError("Control plane requires HTTPS")
        if len(config.get("worker_token", "")) < 32:
            raise ValueError("Worker token missing")
        self.config = config
        self.origin = f"{parsed.scheme}://{parsed.netloc}"
        self.opener = urllib.request.build_opener(SameOriginRedirect(self.origin))

    def request(
        self,
        path: str,
        method: str = "POST",
        data: dict | bytes | None = None,
        headers: dict | None = None,
    ):
        if not path.startswith("/api/") or path.startswith("//"):
            raise ValueError("Control-plane path must start /api/")
        auth = {"Authorization": "Bearer " + self.config["worker_token"]}
        if self.config.get("site_token"):
            auth["OAI-Sites-Authorization"] = "Bearer " + self.config["site_token"]
        auth.update(headers or {})
        if isinstance(data, dict):
            payload = json.dumps(data).encode()
            auth["Content-Type"] = "application/json"
        else:
            payload = data
        req = urllib.request.Request(
            self.origin + path, data=payload, headers=auth, method=method
        )
        with self.opener.open(req, timeout=20) as response:
            body = response.read(2_000_001)
        if len(body) > 2_000_000:
            raise ValueError("Control-plane response exceeded bound")
        return json.loads(body)


def execution_environment() -> dict[str, str]:
    env = sanitize_environment()
    for name in (
        "NVIDIA_API_KEY",
        "GEMINI_API_KEY",
        "AEON_MODEL_BACKEND",
        "AEON_CODEX_BINARY",
    ):
        if os.environ.get(name):
            env[name] = os.environ[name]
    # No worker/admin/Sites credentials passed into generated-code process.
    return env


def docker_command(job_root: Path, image: str, name: str) -> list[str]:
    if not re.fullmatch(r"aeon-job-[a-f0-9-]+", name):
        raise ValueError("Invalid container name")
    return [
        "docker",
        "run",
        "--rm",
        "--init",
        "--name",
        name,
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        "256",
        "--memory",
        "2g",
        "--cpus",
        "2",
        "--shm-size",
        "1g",
        "--tmpfs",
        "/tmp:rw,nosuid,size=512m",
        "--env",
        "GEMINI_API_KEY",
        "--env",
        "NVIDIA_API_KEY",
        "--volume",
        str(job_root.resolve()) + ":/job",
        image,
        "python",
        "-m",
        "aeon_enterprise.execute",
        "--job-root",
        "/job",
    ]


def stop_process(process: subprocess.Popen, container: str | None = None) -> None:
    if container:
        subprocess.run(
            ["docker", "rm", "-f", container],
            capture_output=True,
            timeout=30,
            check=False,
        )
    elif os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            timeout=15,
            check=False,
        )
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


def public_result(result: dict, root: Path) -> dict:
    output = {
        k: v
        for k, v in result.items()
        if k not in {"run_dir", "workspace", "inspections"}
    }
    output["workspace"] = "worker job workspace"
    output["artifacts"] = [Path(p).name for p in result.get("artifacts", [])]
    output["artifact_records"] = [
        {**item, "path": Path(item["path"]).name}
        for item in result.get("artifact_records", [])
    ]
    for key in (
        "decision_summaries",
        "initiatives",
        "sources",
        "findings",
        "local_interaction_checks",
    ):
        if isinstance(output.get(key), list):
            output[key] = output[key][:20]
    if len(json.dumps(output).encode()) > 110000:
        output = {
            k: output[k]
            for k in (
                "task_id",
                "status",
                "reason",
                "artifacts",
                "model_tokens",
                "audit_valid",
                "unresolved_gaps",
                "provider_route",
            )
            if k in output
        }
        output["evidence_note"] = (
            "Full runtime result available in evidence/runtime-result.json"
        )
    return output


def deliver(client: Client, job: dict, lease: str, root: Path, result: dict) -> None:
    workspace = (root / "workspace").resolve()
    uploads = []
    for p in result.get("artifacts", []):
        # Docker reports /job paths; translate only within its declared workspace.
        normalized = str(p).replace("\\", "/")
        path = (
            (workspace / normalized[15:]).resolve()
            if normalized.startswith("/job/workspace/")
            else Path(p).resolve()
        )
        if workspace not in path.parents or not path.is_file() or path.is_symlink():
            raise PermissionError("Artifact escapes task workspace")
        uploads.append((path, path.relative_to(workspace).as_posix()))
    result_file = root / "runtime-result.json"
    if result_file.is_file():
        uploads.append((result_file, "evidence/runtime-result.json"))
    evidence = root / "state" / ("task-" + job["id"][4:]) / "evidence"
    if evidence.is_dir():
        uploads.extend(
            (p, "evidence/" + p.name)
            for p in sorted(evidence.glob("*.png"))[:8]
            if p.is_file() and not p.is_symlink()
        )
    if uploads:
        bundle = root / "deliverables.zip"
        with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as archive:
            for path, relative in uploads:
                archive.write(path, relative)
        uploads.append((bundle, "deliverables.zip"))
    if len(uploads) > 64 or sum(p.stat().st_size for p, _ in uploads) > 32_000_000:
        raise ValueError("Artifact delivery quota exceeded")
    for path, relative in uploads:
        if path.stat().st_size > 8_000_000:
            raise ValueError("Artifact too large")
        client.request(
            f"/api/worker/jobs/{job['id']}/heartbeat",
            data={
                "lease_token": lease,
                "progress": {
                    "phase": "delivering",
                    "steps": int(result.get("steps", 0)),
                    "tokens": int(result.get("model_tokens", 0)),
                },
            },
        )
        client.request(
            f"/api/worker/jobs/{job['id']}/artifacts?path="
            + urllib.parse.quote(relative, safe=""),
            "PUT",
            path.read_bytes(),
            {"X-Lease-Token": lease},
        )
    client.request(
        f"/api/worker/jobs/{job['id']}/finish",
        data={"lease_token": lease, "result": public_result(result, root)},
    )


def process_job(
    client: Client, claim: dict, root: Path, *, trusted_local: bool, image: str
) -> dict:
    job = claim["job"]
    lease = claim["lease_token"]
    if not re.fullmatch(r"job_[a-f0-9]{32}", job["id"]):
        raise ValueError("Invalid job ID")
    directory = root / job["id"]
    directory.mkdir(parents=True, exist_ok=True)
    with file_lock(directory / "supervisor.lock"):
        atomic_write_json(directory / "job.json", job)
        result_path = directory / "runtime-result.json"
        # Existing result must not be delivered as a new attempt before execution.
        if result_path.exists():
            result_path.unlink()
        container = None
        if trusted_local:
            command = [
                sys.executable,
                "-m",
                "aeon_enterprise.execute",
                "--job-root",
                str(directory),
            ]
        else:
            if not shutil.which("docker"):
                raise RuntimeError(
                    "Docker required; use trusted-local only for owner-private work"
                )
            container = "aeon-job-" + job["id"][4:] + "-" + lease[:8]
            command = docker_command(directory, image, container)
        with (directory / "process.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                command,
                env=execution_environment(),
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=os.name != "nt",
            )
            started = time.monotonic()
            last_beat = 0.0
            try:
                while process.poll() is None:
                    if time.monotonic() - started > job["deadline_minutes"] * 60 + 120:
                        stop_process(process, container)
                        break
                    if time.monotonic() - last_beat >= 20:
                        checkpoints = list(
                            (directory / "state").glob("task-*/checkpoint.json")
                        )
                        state = read_json(checkpoints[0], {}) if checkpoints else {}
                        client.request(
                            f"/api/worker/jobs/{job['id']}/heartbeat",
                            data={
                                "lease_token": lease,
                                "progress": {
                                    "phase": str(state.get("phase", "starting")),
                                    "steps": int(state.get("steps", 0)),
                                    "tokens": int(state.get("tokens", 0)),
                                },
                            },
                        )
                        last_beat = time.monotonic()
                    time.sleep(1)
            except BaseException:
                stop_process(process, container)
                raise
        result = read_json(result_path, None)
        if result is None:
            result = {
                "status": "interrupted",
                "reason": "worker_process_stopped",
                "artifacts": [],
                "model_tokens": 0,
                "audit_valid": False,
                "unresolved_gaps": [
                    "Worker process stopped; inspect checkpoint before retrying external actions."
                ],
            }
            checkpoints = list((directory / "state").glob("task-*/checkpoint.json"))
            if checkpoints:
                result["model_tokens"] = read_json(checkpoints[0], {}).get("tokens", 0)
            atomic_write_json(result_path, result)
        deliver(client, job, lease, directory, result)
        return result


def main() -> int:
    p = argparse.ArgumentParser(description="AEON Enterprise outbound worker")
    p.add_argument("--connection", type=Path, required=True)
    p.add_argument("--state-root", type=Path, required=True)
    p.add_argument("--trusted-local", action="store_true")
    p.add_argument(
        "--allow-local",
        action="store_true",
        help="Explicit localhost integration testing only",
    )
    p.add_argument("--image", default="aeon-enterprise-worker:0.4.0")
    p.add_argument("--once", action="store_true")
    a = p.parse_args()
    config = read_json(a.connection, None)
    if not isinstance(config, dict):
        p.error("Connection file missing or invalid")
    if bool(config.get("mode") == "trusted-local") != a.trusted_local:
        p.error("Execution mode must match enrolled worker")
    if not a.trusted_local and not shutil.which("docker"):
        p.error("Docker unavailable; no automatic downgrade to local execution")
    client = Client(config, allow_local=a.allow_local)
    root = a.state_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    with file_lock(root / "worker.lock"):
        while True:
            try:
                claim = client.request("/api/worker/claim", data={})
                if claim.get("job"):
                    result = process_job(
                        client,
                        claim,
                        root,
                        trusted_local=a.trusted_local,
                        image=a.image,
                    )
                    print(
                        json.dumps(
                            {
                                "job_id": claim["job"]["id"],
                                "status": result["status"],
                                "tokens": result.get("model_tokens", 0),
                            }
                        ),
                        flush=True,
                    )
                elif a.once:
                    print('{"status":"idle"}', flush=True)
                if a.once:
                    return 0
                time.sleep(5)
            except KeyboardInterrupt:
                return 130
            except Exception as error:
                print(
                    json.dumps(
                        {"status": "worker_error", "type": type(error).__name__}
                    ),
                    flush=True,
                )
                if a.once:
                    return 1
                time.sleep(15)


if __name__ == "__main__":
    raise SystemExit(main())
