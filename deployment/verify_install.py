"""Verify a wheel in a clean venv outside the source checkout.

Creates evidence, does not remove existing files. Optional --browser installs the
deployment extra and launches real Chromium. No model credentials are forwarded.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--requirements", type=Path)
    parser.add_argument("--browser", action="store_true")
    parser.add_argument("--wheelhouse", type=Path, help="Offline dependency wheels for this OS/Python version")
    args = parser.parse_args()
    wheel = args.wheel.resolve(strict=True)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    environment = {key: value for key, value in os.environ.items() if not re.search(r"KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|PRIVATE", key, re.IGNORECASE) and key not in {"PYTHONPATH", "PYTHONHOME"}}
    events = []
    def run(command: list[str], timeout: int = 120) -> str:
        started = time.perf_counter()
        try:
            process = subprocess.run(command, cwd=output, env=environment, text=True, encoding="utf-8", errors="replace",
                                     capture_output=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired as error:
            events.append({"command": command, "returncode": "timeout", "seconds": timeout,
                           "stdout": str(error.stdout or ""), "stderr": str(error.stderr or "")})
            (output / "install-evidence.json").write_text(json.dumps(events, indent=2), encoding="utf-8")
            raise
        events.append({"command": command, "returncode": process.returncode, "seconds": round(time.perf_counter() - started, 3),
                       "stdout": process.stdout, "stderr": process.stderr})
        (output / "install-evidence.json").write_text(json.dumps(events, indent=2), encoding="utf-8")
        if process.returncode:
            raise RuntimeError(f"Install check failed: {command[0]} ({process.returncode}); see install-evidence.json")
        return process.stdout
    run([sys.executable, "-m", "venv", str(output / "venv")])
    python = output / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    command = [str(python), "-m", "pip", "install", "--disable-pip-version-check", "--timeout", "30", "--retries", "2"]
    if args.wheelhouse:
        command += ["--no-index", "--find-links", str(args.wheelhouse.resolve(strict=True))]
    if args.requirements:
        command += ["-c", str(args.requirements.resolve(strict=True))]
    command += [str(wheel) + ("[deployment]" if args.browser else "")]
    run(command, timeout=240)
    run([str(python), "-c", "import aeon_worker,sys,importlib.metadata as m; from pathlib import Path; assert Path(aeon_worker.__file__).is_relative_to(Path(sys.prefix)); print(m.version('codebee-improve')); print(aeon_worker.__file__)"])
    run([str(python), "-m", "aeon_worker", "--help"])
    run([str(python), "-m", "aeon_worker", "--task-root", str(output / "tasks"), "smoke", "--workspace", str(output / "work")])
    single_result = run([str(python), "-m", "aeon_worker", "--task-root", str(output / "tasks"), "--adapter", "aeon_worker.demo:create_adapter", "task", "start",
                        "--result-only", "--brief", "Write aeon-smoke.json. No research.", "--workspace", str(output / "custom-work")])
    assert json.loads(single_result)["status"] == "completed"
    if args.browser:
        run([str(python), "-m", "playwright", "install", "chromium"], timeout=240)
        browser_script = '''
from pathlib import Path
from aeon_worker.models import ActionGrant
from aeon_worker.tools import WorkspaceTools
from aeon_worker.site import render_site
from aeon_worker.verification import InspectionCache, verify_artifacts
tools = WorkspaceTools(Path("browser-work"), Path("browser-evidence"), ActionGrant())
try:
    tools.write_file("index.html", render_site({"title": "Installed wheel check", "intro": "Portable browser fixture"}))
    cache = InspectionCache()
    for _ in range(2):
        findings, inspections = verify_artifacts(tools, ["index.html"], "website", [], inspection_cache=cache)
        assert not findings, findings
        assert all(Path(path).is_file() for path in inspections[0]["screenshots"])
    assert cache.hits == 1 and cache.misses == 1
    print("desktop/mobile Chromium checks passed; cache hit confirmed")
finally:
    tools.close()
'''
        run([str(python), "-c", browser_script])
    run([str(python), "-m", "pip", "check"])
    print(json.dumps({"status": "passed", "checks": len(events), "browser": args.browser, "evidence": str(output / "install-evidence.json"), "python": str(python)}))


if __name__ == "__main__":
    main()
