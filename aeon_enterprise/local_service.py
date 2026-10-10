"""Explicit loopback pilot supervisor; never reads hosted connection credentials."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import urllib.parse
import urllib.request

from aeon_enterprise.worker import Client, SameOriginRedirect, main as worker_main
from codebee_improve.storage import atomic_write_json, file_lock, read_json


def local_origin(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in {"", "/"} or not parsed.port):
        raise ValueError("Local worker requires an explicit HTTP loopback origin and port")
    return f"{parsed.scheme}://{parsed.netloc}"


def local_root(path: Path) -> Path:
    root = path.resolve()
    if os.environ.get("LOCALAPPDATA"):
        hosted = (Path(os.environ["LOCALAPPDATA"]) / "AEON" / "enterprise-private").resolve()
        if root == hosted or hosted in root.parents:
            raise ValueError("Local worker state cannot use the hosted installation")
    return root


def call(origin: str, path: str, data: dict | None = None) -> dict:
    origin = local_origin(origin)
    if not path.startswith("/api/") or path.startswith("//"):
        raise ValueError("Local API path required")
    headers = {"Origin": origin, "Content-Type": "application/json"}
    request = urllib.request.Request(origin + path, headers=headers,
        data=json.dumps(data).encode() if data is not None else None,
        method="POST" if data is not None else "GET")
    opener = urllib.request.build_opener(SameOriginRedirect(origin))
    with opener.open(request, timeout=15) as response:
        body = response.read(2_000_001)
    if len(body) > 2_000_000:
        raise ValueError("Local API response exceeded bound")
    result = json.loads(body)
    if not isinstance(result, dict):
        raise ValueError("Local API object required")
    return result


def enroll(origin: str, root: Path) -> dict:
    origin = local_origin(origin)
    root = local_root(root)
    root.mkdir(parents=True, exist_ok=True)
    runtime = call(origin, "/api/local/runtime")
    if runtime.get("mode") != "local" or runtime.get("persistence") is not True:
        raise ValueError("Persistent local runtime required before enrolling worker")
    call(origin, "/api/session")
    path = root / "worker-connection.json"
    with file_lock(root / "enrollment.lock"):
        dashboard = call(origin, "/api/orgs/org_primary/dashboard")
        config = read_json(path, None)
        if config:
            Client(config, allow_local=True)
            if config.get("base_url") != origin or config.get("mode") != "trusted-local" or config.get("site_token"):
                raise ValueError("Saved local connection belongs to a different origin or execution mode")
            if any(w.get("id") == config.get("worker_id") and not w.get("revoked")
                   for w in dashboard.get("workers", [])):
                return config
        result = call(origin, "/api/orgs/org_primary/workers", {
            "name": "Local personal worker", "mode": "trusted-local"})
        config = result["connection"]
        Client(config, allow_local=True)
        if config.get("base_url") != origin or config.get("mode") != "trusted-local" or config.get("site_token"):
            raise ValueError("Unexpected local enrollment authority")
        atomic_write_json(path, config)
        if os.name != "nt":
            path.chmod(0o600)
        return config


def load_providers(provider_file: Path | None) -> bool:
    if provider_file:
        providers = read_json(provider_file, None)
        if not isinstance(providers, dict):
            raise ValueError("Provider credential file missing or invalid")
        for name in ("NVIDIA_API_KEY", "GEMINI_API_KEY"):
            value = providers.get(name)
            if value is not None:
                if not isinstance(value, str) or not value.strip():
                    raise ValueError("Provider credential must be a nonempty string")
                os.environ[name] = value
    return any(os.environ.get(name) for name in ("NVIDIA_API_KEY", "GEMINI_API_KEY"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AEON loopback worker (trusted owner pilot)")
    parser.add_argument("--origin", default="http://127.0.0.1:8787")
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--provider-file", type=Path)
    parser.add_argument("--browsers", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args(argv)
    origin = local_origin(args.origin)
    root = local_root(args.state_root)
    available = load_providers(args.provider_file)
    if args.browsers:
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(args.browsers.resolve())
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        browser_ready = Path(playwright.chromium.executable_path).is_file()
    if args.check:
        print(json.dumps({"mode": "local", "provider_available": available, "browser_ready": browser_ready}))
        return 0 if available and browser_ready else 1
    if not available or not browser_ready:
        raise RuntimeError("Local worker needs model credentials and Chromium; run --check first")
    enroll(origin, root)
    worker_args = ["--connection", str(root / "worker-connection.json"),
        "--state-root", str(root / "jobs"), "--trusted-local", "--allow-local"]
    if args.once:
        worker_args.append("--once")
    return worker_main(worker_args)


if __name__ == "__main__":
    raise SystemExit(main())
