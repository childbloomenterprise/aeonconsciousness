"""Installed supervisor launcher; configuration and state stay outside the checkout."""

from __future__ import annotations

import argparse
from importlib.metadata import version
import json
import os
from pathlib import Path
import sys

from aeon_enterprise.worker import Client, main as worker_main


def configure(root: Path) -> dict:
    connection = root / "worker-connection.json"
    config = json.loads(connection.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("Worker connection must be an object")
    Client(config)
    if config.get("mode") not in {"trusted-local", "docker"}:
        raise ValueError("Connection requires an explicit enrolled execution mode")
    provider_file = root / "providers.json"
    providers = (
        json.loads(provider_file.read_text(encoding="utf-8"))
        if provider_file.exists()
        else {}
    )
    if not isinstance(providers, dict):
        raise ValueError("Provider configuration must be an object")
    for name in ("NVIDIA_API_KEY", "GEMINI_API_KEY"):
        value = providers.get(name)
        if value is not None:
            if not isinstance(value, str) or not value.strip():
                raise ValueError("Provider credential must be a nonempty string")
            os.environ[name] = value
    # Browser binaries belong to this installation, not a disposable tool cache.
    browsers = root / "browsers"
    if browsers.is_dir():
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers)
    return config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AEON installed worker service")
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--check", action="store_true", help="Check local installation without claiming work")
    args = parser.parse_args(argv)
    root = args.private_root.resolve()
    config = configure(root)
    if args.check:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser_ready = Path(playwright.chromium.executable_path).is_file()
        provider_available = any(os.environ.get(name) for name in ("NVIDIA_API_KEY", "GEMINI_API_KEY"))
        print(json.dumps({
            "version": version("codebee-improve"),
            "python": sys.version.split()[0],
            "mode": config["mode"],
            "provider_available": provider_available,
            "browser_ready": browser_ready,
        }))
        return 0 if provider_available and browser_ready else 1
    worker_args = ["--connection", str(root / "worker-connection.json"), "--state-root", str(root / "jobs")]
    if config["mode"] == "trusted-local":
        worker_args.append("--trusted-local")
    if args.once:
        worker_args.append("--once")
    return worker_main(worker_args)


if __name__ == "__main__":
    raise SystemExit(main())
