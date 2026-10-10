"""Round-3 objective verifier: machine-check both arms' deliverables against brief acceptance criteria."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "briefs-complex-round3.json").read_text(encoding="utf-8"))


def words(text: str) -> int:
    return len(re.findall(r"\S+", text))


SECTION_HEADS = [
    {"id": "complex-brief-underfill",
     "heads": ["Ambiguities Identified", "Decisions Without Asking", "Must Confirm With Client"]},
    {"id": "complex-user-intent-truncated",
     "heads": ["What The User Actually Needs", "Facts vs Inferences", "What I Cannot Know From This Fragment", "Reply I Would Send"]},
]


def heads_ok(text: str, required: list[str]) -> bool:
    normalized = text.replace("#", "").lower()
    return all(head.lower() in normalized for head in required)


def enumerated_count(text: str) -> int:
    return len(re.findall(r"^\s*(?:[-*•]|\d+[.)])\s", text, flags=re.M))


def verify(task: dict, folder: Path) -> dict:
    results = []
    file_name = task["accept"]["require"][0]
    path = folder / file_name
    exists = path.is_file() and path.stat().st_size > 0
    if not exists:
        return {"task": task["id"], "passed": 0, "total": len(task["accept"]["checks"]),
                "results": [{"check": "file exists and nonempty", "pass": False}], "missing_file": True}
    text = path.read_text(encoding="utf-8", errors="replace")
    tid = task["id"]
    for check in task["accept"]["checks"]:
        c = check.lower()
        passed = True  # evaluated below
        if "file exists and nonempty" in c:
            passed = path.is_file() and path.stat().st_size > 0
            results.append({"check": check, "pass": passed})
            continue
        if "at most" in c and "words" in c:
            limit = int(re.search(r"at most (\d+) words", c).group(1))
            passed = words(text) <= limit
        elif "section heads" in c or "required section" in c:
            heads = next(h["heads"] for h in SECTION_HEADS if h["id"] == tid)
            passed = heads_ok(text, heads)
        elif "at least 5 enumerated ambiguities" in c:
            ambiguities = re.search(r"Ambiguities Identified(.*?)(?:##?\s*Decisions|$)", text, flags=re.S | re.I)
            passed = bool(ambiguities) and enumerated_count(ambiguities.group(1)) >= 5
        elif "at least 3 must-confirm" in c:
            confirm = re.search(r"Must Confirm With Client(.*)$", text, flags=re.S)
            passed = bool(confirm) and enumerated_count(confirm.group(1)) >= 3
        elif "reversibility" in c:
            passed = bool(re.search(r"\b(default|reversible|reversibility|safe|placeholder)\b", text, flags=re.I))
        elif "statuslevel" in c:
            passed = bool(re.search(r"(const|let|var)\s+statusLevel\b", text)) and \
                     bool(re.search(r"(green|amber|red)", text))
        elif "feed_url" in c:
            passed = len(re.findall(r"FEED_URL\s*=", text)) == 1
        elif "2000ms" in c or "2 seconds" in c or "setinterval" in c:
            passed = bool(re.search(r"setInterval\s*\([^,]+,\s*(2000|2_000)\s*\)", text))
        elif "normalizefeed" in c:
            passed = bool(re.search(r"function\s+normalizeFeed|normalizeFeed\s*=", text)) and "TODO" in text
        elif "offline" in c or "live-data-unavailable" in c or "fallback" in c:
            passed = bool(re.search(r"(unavailable|offline|last good|lastGood|catch)", text, flags=re.I))
        elif "known limitations" in c:
            limits = re.search(r"Known Limitations(.*)$", text, flags=re.S | re.I)
            passed = bool(limits) and enumerated_count(limits.group(1)) >= 2
        elif "at least 4 cannot-know" in c:
            cannot = re.search(r"Cannot Know(.*)$", text, flags=re.S | re.I)
            passed = bool(cannot) and enumerated_count(cannot.group(1)) >= 4
        elif "confidence" in c:
            passed = all(tok in text.lower() for tok in ("high", "medium", "low"))
        elif "does not promise" in c or "no 'will be fixed" in c:
            passed = not re.search(r"(will be fixed by|guaranteed|fixed by \d|done by \d|resolved by \d)", text, flags=re.I)
        elif "row-count as definite" in c or "unqualified 'the bug is'" in c:
            passed = (not re.search(r"the bug is", text, flags=re.I)) or \
                     bool(re.search(r"(may|might|could|possibly|one possibility|hypothes)", text, flags=re.I))
        elif "no fabricated brand" in c or "do not invent" in c or "no invented" in c:
            passed = not re.search(r"(our product is called|our brand is|called \'?[A-Z][a-z]+\')", text)
        elif "parses as html" in c:
            passed = bool(re.search(r"<!doctype html|<html[\s>]", text, flags=re.I))
        else:
            passed = None  # manual / pattern unmatched
        results.append({"check": check, "pass": passed})
    total = len(results)
    known = [r for r in results if r["pass"] is not None]
    return {"task": tid, "passed": sum(1 for r in known if r["pass"]), "total": total,
            "manual_only": total - len(known), "results": results}


def main():
    import zipfile
    output = {}
    for arm, base in (("framework", ROOT), ("standalone", ROOT / "standalone-complex")):
        output[arm] = {}
        for task in CONFIG["tasks"]:
            folder = base / task["id"]
            if arm == "framework":
                downloads = folder / "downloads"
                deliverable = None
                if downloads.is_dir():
                    matches = sorted(downloads.rglob(task["accept"]["require"][0]))
                    deliverable = matches[0] if matches else None
                    if deliverable is None:
                        for zpath in sorted(downloads.glob("*.zip")):
                            try:
                                with zipfile.ZipFile(zpath) as archive:
                                    member = next((n for n in archive.namelist()
                                                   if n.replace("\\", "/").rstrip("/").endswith(task["accept"]["require"][0])
                                                   and not n.startswith("evidence")), None)
                                if member:
                                    staging = folder / "verified-zip"
                                    staging.mkdir(exist_ok=True)
                                    with zipfile.ZipFile(zpath) as archive:
                                        (staging / task["accept"]["require"][0]).write_bytes(archive.read(member))
                                    deliverable = staging / task["accept"]["require"][0]
                                    break
                            except (zipfile.BadZipFile, OSError):
                                continue
                if deliverable:
                    staging = folder / "verified"
                    if deliverable.parent.name != "verified-zip":
                        staging.mkdir(exist_ok=True)
                        target = staging / task["accept"]["require"][0]
                        target.write_bytes(deliverable.read_bytes())
                        folder_use = staging
                    else:
                        folder_use = deliverable.parent
                else:
                    folder_use = folder
            else:
                folder_use = folder
            output[arm][task["id"]] = verify(task, folder_use)
    out = ROOT / "verification-round3.json"
    out.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for arm, tasks in output.items():
        for tid, verdict in tasks.items():
            print(json.dumps({"arm": arm, "task": tid, "passed": verdict["passed"],
                              "total": verdict["total"], "manual_only": verdict.get("manual_only", 0)}))


if __name__ == "__main__":
    main()
