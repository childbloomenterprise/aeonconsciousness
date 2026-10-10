"""Mechanical artifact checks independent of model self-report."""

from __future__ import annotations

import csv
import copy
import hashlib
import json
import re
import time
from itertools import islice
from pathlib import Path
import urllib.parse
from html.parser import HTMLParser
from typing import Any

from .models import VerificationFinding
from .tools import WorkspaceTools


class InspectionCache:
    """Short-lived, run-local cache for successful, entirely local previews.

    Hash every workspace file, including undeclared assets. Large workspaces
    bypass caching instead of weakening invalidation. Mechanical checks still
    run each time. Failed and remote-dependent inspections are never cached.
    """

    def __init__(self, *, enabled: bool = True, ttl_seconds: float = 120.0) -> None:
        self.enabled = enabled
        self.ttl_seconds = ttl_seconds
        self.entries: dict[tuple[str, str, str], tuple[float, dict[str, Any]]] = {}
        self.hits = 0
        self.misses = 0

    def clear(self) -> None:
        self.entries.clear()

    def _signature(self, tools: WorkspaceTools) -> str | None:
        digest = hashlib.sha256()
        size = 0
        try:
            for index, path in enumerate(sorted(islice(tools.workspace.rglob("*"), 513))):
                if index >= 512 or path.is_symlink():
                    return None
                if not path.is_file():
                    continue
                size += path.stat().st_size
                if size > 8_000_000:
                    return None
                digest.update(path.relative_to(tools.workspace).as_posix().encode("utf-8") + b"\0")
                digest.update(hashlib.sha256(path.read_bytes()).digest())
        except OSError:
            return None
        return digest.hexdigest()

    def inspect(self, tools: WorkspaceTools, relative: str) -> dict[str, Any]:
        signature = self._signature(tools) if self.enabled else None
        key = (str(tools.workspace), relative, signature or "")
        cached = self.entries.get(key) if signature else None
        if cached and time.monotonic() - cached[0] < self.ttl_seconds and all(tools.evidence_dir in Path(path).parents and Path(path).is_file() for path in cached[1].get("screenshots", [])):
            self.hits += 1
            return copy.deepcopy(cached[1])
        self.misses += 1
        result = tools.inspect_site(relative)
        if signature and not result.get("issues") and not result.get("remote_requests") and self._signature(tools) == signature:
            self.entries = {existing: value for existing, value in self.entries.items() if existing[0] != str(tools.workspace) or existing[2] == signature}
            self.entries[key] = (time.monotonic(), copy.deepcopy(result))
        return result


def _source_key(url: str) -> str:
    return urllib.parse.urldefrag(url.rstrip(".,;"))[0]


def cited_urls(content: str) -> set[str]:
    """Extract source links without treating URLs in code examples as claims."""
    prose = re.sub(r"```[\s\S]*?```", "", content)
    prose = re.sub(r"`[^`\n]*`", "", prose)
    links = set(re.findall(r"\[[^\]]+\]\((https?://[^\s)]+)\)", prose))
    for line in prose.splitlines():
        if re.search(r"\b(?:source|reference|citation|documentation)\b", line[:100], re.IGNORECASE):
            links.update(re.findall(r"https?://[^\s<>()\[\]\"']+", line))
    if not links:
        links.update(re.findall(r"https?://[^\s<>()\[\]\"']+", prose))
    return links


class _HTMLChecks(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = False
        self.lang = False
        self.viewport = False
        self.links: list[str] = []
        self.images_without_alt = 0
        self.ids: set[str] = set()
        self.forms = 0
        self.form_has_action = False
        self.visible_parts: list[str] = []
        self.skip_text = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        fields = dict(attrs)
        if tag in {"script", "style", "noscript"}:
            self.skip_text += 1
        if fields.get("id"):
            self.ids.add(str(fields["id"]))
        if tag == "html" and fields.get("lang"):
            self.lang = True
        if tag == "title":
            self.title = True
        if tag == "meta" and fields.get("name", "").lower() == "viewport":
            self.viewport = True
        if tag == "a" and fields.get("href"):
            self.links.append(str(fields["href"]))
        if tag == "link" and fields.get("href"):
            self.links.append(str(fields["href"]))
        if tag == "script" and fields.get("src"):
            self.links.append(str(fields["src"]))
        if tag == "img":
            if fields.get("src"):
                self.links.append(str(fields["src"]))
            if "alt" not in fields:
                self.images_without_alt += 1
        if tag == "form":
            self.forms += 1
            self.form_has_action = self.form_has_action or bool(fields.get("action"))

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"}:
            self.skip_text = max(0, self.skip_text - 1)

    def handle_data(self, data: str) -> None:
        if not self.skip_text and data.strip():
            self.visible_parts.append(" ".join(data.split()))


def verify_artifacts(
    tools: WorkspaceTools,
    artifact_paths: list[str],
    task_type: str,
    sources: list[dict[str, Any]],
    *, inspection_cache: InspectionCache | None = None,
    require_sources: bool = True,
) -> tuple[list[VerificationFinding], list[dict[str, Any]]]:
    findings: list[VerificationFinding] = []
    inspections: list[dict[str, Any]] = []
    if not artifact_paths:
        findings.append(VerificationFinding("error", "task", "No deliverable file was produced."))
        return findings, inspections
    for relative in sorted(set(artifact_paths)):
        try:
            path = tools._path(relative)
        except PermissionError:
            findings.append(VerificationFinding("error", relative, "Artifact path escapes workspace."))
            continue
        if not path.is_file() or path.stat().st_size == 0:
            findings.append(VerificationFinding("error", relative, "Artifact missing or empty."))
            continue
        suffix = path.suffix.lower()
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append(VerificationFinding("error", relative, "Artifact is not UTF-8 text."))
            continue
        if suffix == ".json":
            try:
                json.loads(content)
            except json.JSONDecodeError as error:
                findings.append(VerificationFinding("error", relative, f"Invalid JSON: {error.msg}."))
        elif suffix == ".csv":
            try:
                rows = list(csv.reader(content.splitlines()))
                if not rows or len(rows[0]) < 2:
                    raise ValueError("CSV needs a header with at least two columns.")
                if any(len(row) != len(rows[0]) for row in rows[1:]):
                    raise ValueError("CSV row width differs from header.")
                if task_type == "browser_file" and "evidence_url" in rows[0]:
                    column = rows[0].index("evidence_url")
                    inspected = {_source_key(item["url"]) for item in sources}
                    for row_number, row in enumerate(rows[1:], start=2):
                        if _source_key(row[column]) not in inspected:
                            findings.append(VerificationFinding("error", relative, f"CSV row {row_number} evidence URL was not inspected: {row[column]}"))
            except (csv.Error, ValueError) as error:
                findings.append(VerificationFinding("error", relative, str(error)))
        elif suffix == ".html":
            parser = _HTMLChecks()
            parser.feed(content)
            if not re.search(r"</html>\s*$", content, re.IGNORECASE) or not re.search(r"</body>\s*</html>\s*$", content, re.IGNORECASE):
                findings.append(VerificationFinding("error", relative, "HTML document is missing its closing body/html tags."))
            for label, passed in (("title", parser.title), ("html lang", parser.lang), ("viewport meta", parser.viewport)):
                if not passed:
                    findings.append(VerificationFinding("error", relative, f"Missing {label}."))
            if parser.images_without_alt:
                findings.append(VerificationFinding("error", relative, "Images without alt text."))
            visible = " ".join(parser.visible_parts)
            if parser.forms and not parser.form_has_action and not re.search(r"\b(?:fetch|XMLHttpRequest|sendBeacon)\s*\(", content) and re.search(r"\b(?:send|submit|register|mailing list|contact|inquiry)\b", visible, re.IGNORECASE) and not re.search(r"\b(?:not sent|not transmitted|no (?:data|registration|message) (?:is )?(?:sent|transmitted)|local[- ]only|demo only|draft only|not connected)\b", visible, re.IGNORECASE):
                findings.append(VerificationFinding("error", relative, "Form has no delivery backend and is not labeled as local-only or a demo."))
            for link in parser.links:
                if link.startswith("#"):
                    if link[1:] and link[1:] not in parser.ids:
                        findings.append(VerificationFinding("error", relative, f"Broken in-page anchor: {link}"))
                    continue
                if link.startswith(("https://", "http://", "mailto:", "tel:", "data:")):
                    continue
                linked = (path.parent / link.split("#", 1)[0].split("?", 1)[0]).resolve()
                if not linked.exists() or tools.workspace not in linked.parents and linked != tools.workspace:
                    findings.append(VerificationFinding("error", relative, f"Broken local link: {link}"))
            try:
                inspection = inspection_cache.inspect(tools, relative) if inspection_cache else tools.inspect_site(relative)
                inspections.append(inspection)
                for issue in inspection["issues"]:
                    findings.append(VerificationFinding("error", relative, issue))
            except Exception as error:
                findings.append(VerificationFinding("error", relative, f"Browser inspection unavailable: {type(error).__name__}: {error}"[:300]))
        elif suffix == ".md" and task_type in {"research", "browser_file"} and require_sources:
            if not sources:
                findings.append(VerificationFinding("error", relative, "Research result has no inspected source pages."))
            else:
                cited = cited_urls(content)
                inspected = {_source_key(item["url"]) for item in sources}
                if not cited:
                    findings.append(VerificationFinding("error", relative, "Research result does not cite a source URL."))
                elif not {_source_key(url) for url in cited} & inspected:
                    findings.append(VerificationFinding("error", relative, "No cited URL matches an inspected source page."))
                for unknown in sorted(url for url in cited if _source_key(url) not in inspected):
                    findings.append(VerificationFinding("error", relative, f"Cited URL was not inspected: {unknown}"))
    return findings, inspections
