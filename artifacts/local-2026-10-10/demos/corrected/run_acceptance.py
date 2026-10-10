"""Bounded independent assertion receipt plus immutable-origin integrity evidence."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
started = datetime.now(timezone.utc).isoformat()
clock = time.monotonic()
command = [sys.executable, str(ROOT / "assertion_check.py")]
process = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
receipt = {"started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(),
           "timeout_seconds": 10, "elapsed_seconds": round(time.monotonic() - clock, 3),
           "command": command, "returncode": process.returncode, "stdout": process.stdout,
           "stderr": process.stderr, "original_worker_execution": False,
           "performed_by": "independent acceptance inspector",
           "scope": "original downloaded JSON plus corrected deliverables; no live API/state changes"}
(ROOT / "assertion-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
if process.returncode:
    raise SystemExit(process.returncode)
observed = json.loads(process.stdout)
assert observed["passed"] is True
files = ("backup-strategy.md", "source-summary.json", "checked-summary.md", "correction-review.md", "assertion_check.py", "assertion-receipt.json")
hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files}
(ROOT / "corrected-hashes.json").write_text(json.dumps({"checked_at": receipt["finished_at"], "sha256": hashes}, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"passed": True, "returncode": process.returncode, "original_worker_execution": False,
                  "original_download_hashes_verified": observed["original_downloads_hashes_verified"],
                  "corrected_artifacts_hashed": len(hashes)}))
