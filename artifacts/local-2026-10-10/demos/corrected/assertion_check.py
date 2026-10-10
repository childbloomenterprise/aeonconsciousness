"""Independent assertions; never execute worker-authored code or mutate originals."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEMOS = ROOT.parent
original = DEMOS / "sqlite-browser-file/downloads/source-summary.json"
corrected = ROOT / "source-summary.json"
checks = []
for label, path in (("original_download", original), ("independent_correction", corrected)):
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert {"title", "source_url", "claims"} <= set(payload)
    assert payload["title"] == "About SQLite"
    assert payload["source_url"] == "https://www.sqlite.org/about.html"
    assert type(payload["claims"]) is list and len(payload["claims"]) == 3
    assert all(type(claim) is str and claim.strip() for claim in payload["claims"])
    checks.append({"label": label, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                   "json_parse": True, "required_fields": True, "exact_title_url": True,
                   "three_nonempty_claim_strings": True})
for path in (DEMOS / "sqlite-browser-file/downloads/checked-summary.md", ROOT / "checked-summary.md"):
    assert "https://www.sqlite.org/about.html" in path.read_text(encoding="utf-8")
for label in ("sqlite-backup-research", "sqlite-browser-file"):
    folder = DEMOS / label
    record = json.loads((folder / "control-plane-result.json").read_text(encoding="utf-8"))
    for artifact in record["artifacts"]:
        raw = (folder / "downloads" / artifact["path"]).read_bytes()
        assert len(raw) == artifact["size"]
        assert hashlib.sha256(raw).hexdigest() == artifact["sha256"]
print(json.dumps({"passed": True, "checks": checks, "original_downloads_hashes_verified": 7,
                  "markdown_citations_present": True,
                  "authority": "independent inspector after original worker completion"}))
