"""Create a source allowlist archive; never include credentials, jobs or caches."""

from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import zipfile

FOLDERS = (
    "aeon_enterprise",
    "aeon_worker",
    "aeon_kernel",
    "aeon_world",
    "agent_lab",
    "codebee_improve",
    "deployment",
    "enterprise",
    "tests",
    "third_party",
    ".github",
    "examples",
)
ROOT_FILES = (
    "pyproject.toml",
    "README.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "MANIFEST.in",
    ".dockerignore",
    ".gitignore",
)
SKIP = {
    "node_modules",
    "dist",
    "generated",
    "__pycache__",
    ".git",
    ".sites-runtime",
    ".wrangler",
}


def allowed(path: Path) -> bool:
    return (
        not any(p in SKIP for p in path.parts)
        and not any(p.startswith(".env") for p in path.parts)
        and path.suffix not in {".pyc", ".sqlite", ".sqlite3", ".log"}
    )


def package(root: Path, output: Path) -> dict:
    files = {root / p for p in ROOT_FILES if (root / p).is_file()}
    for folder in FOLDERS:
        files.update(
            p
            for p in (root / folder).rglob("*")
            if p.is_file() and allowed(p.relative_to(root))
        )
    files.update(p for p in (root / "docs").glob("*.md"))
    for name in (
        "aeon-worker-grant.example.json",
        "aeon-world.governed-scripted.json",
        "aeon-worker-benchmark-30.json",
        "aeon-worker-benchmark-holdout-30-v2.json",
        "aeon-nat-workflow.yml",
    ):
        files.add(root / "configs" / name)
    secrets = [
        os.environ[k].encode()
        for k in (
            "GEMINI_API_KEY",
            "NVIDIA_API_KEY",
            "AEON_ADMIN_KEY",
            "AEON_SITE_SERVICE_KEY",
        )
        if os.environ.get(k)
    ]
    for p in files:
        if any(secret in p.read_bytes() for secret in secrets):
            raise ValueError("Configured credential found in source archive input")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        output, "w", zipfile.ZIP_DEFLATED, strict_timestamps=False
    ) as archive:
        for p in sorted(files):
            archive.write(p, p.relative_to(root).as_posix())
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    result = {
        "version": "0.4.0",
        "archive": str(output),
        "sha256": digest,
        "files": len(files),
        "configured_credential_scan": "passed",
    }
    output.with_suffix(".manifest.json").write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    a = parser.parse_args()
    print(json.dumps(package(a.root.resolve(), a.output.resolve())))
