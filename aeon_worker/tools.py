"""Bounded public-web, local-file, command, and browser tools for one task."""

from __future__ import annotations

import html
import hashlib
import ipaddress
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from .models import ActionGrant
from .site import render_site


FILE_SUFFIXES = frozenset({
    ".md", ".txt", ".html", ".css", ".js", ".mjs", ".jsx", ".ts", ".tsx",
    ".py", ".json", ".csv", ".svg", ".yaml", ".yml", ".toml",
})
MAX_FILE_BYTES = 1_000_000


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.anchors: dict[str, int] = {}
        self.skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        anchor = dict(attrs).get("id")
        if anchor and not self.skip:
            self.anchors[anchor] = len(self.parts)
        if tag in {"script", "style", "noscript"}:
            self.skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"}:
            self.skip = max(0, self.skip - 1)

    def handle_data(self, data: str) -> None:
        if not self.skip:
            clean = " ".join(data.split())
            if clean:
                self.parts.append(clean)


class _DuckDuckGoResults(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._field = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        fields = dict(attrs)
        classes = (fields.get("class") or "").split()
        if tag == "a" and "result-link" in classes:
            raw = html.unescape(fields.get("href") or "")
            parsed = urllib.parse.urlparse(raw)
            link = urllib.parse.parse_qs(parsed.query).get("uddg", [raw])[0]
            try:
                _public_url(link)
            except ValueError:
                return
            self.results.append({"title": "", "url": link, "snippet": ""})
            self._field = "title"
        elif tag == "td" and "result-snippet" in classes and self.results:
            self._field = "snippet"

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._field == "title" or tag == "td" and self._field == "snippet":
            self._field = ""

    def handle_data(self, data: str) -> None:
        if self._field and self.results:
            self.results[-1][self._field] += " ".join(data.split()) + " "


def _public_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Only public HTTP(S) URLs are allowed.")
    host = parsed.hostname.lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith((".local", ".internal", ".test")):
        raise ValueError("Local/private hosts are unavailable to public-web tools.")
    try:
        addresses = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror as error:
        raise ValueError("URL host could not be resolved.") from error
    for record in addresses:
        address = ipaddress.ip_address(record[4][0])
        if not address.is_global:
            raise ValueError("Private/reserved network address is unavailable.")
    return url


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        _public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _fetch(url: str, *, max_bytes: int = 350_000) -> tuple[str, str]:
    _public_url(url)
    opener = urllib.request.build_opener(_SafeRedirect())
    request = urllib.request.Request(url, headers={"User-Agent": "AEON-Worker/0.1 (personal research)"})
    with opener.open(request, timeout=20) as response:
        final_url = _public_url(response.geturl())
        content_type = response.headers.get_content_type()
        if content_type not in {"text/html", "text/plain", "application/xml", "text/xml", "application/rss+xml"}:
            raise ValueError("URL did not return a supported text document.")
        raw = response.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise ValueError("Web page exceeded size limit.")
        encoding = response.headers.get_content_charset() or "utf-8"
    return final_url, raw.decode(encoding, errors="replace")


def _host_matches(host: str, allowed: tuple[str, ...]) -> bool:
    return any(host == domain or host.endswith("." + domain) for domain in allowed)


class WorkspaceTools:
    def __init__(self, workspace: Path, evidence_dir: Path, grant: ActionGrant, *, spent: float = 0.0):
        self.workspace = workspace.resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.evidence_dir = evidence_dir.resolve()
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.grant = grant
        self.spent = spent
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._write_guard_active = False

    def close(self) -> None:
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def _path(self, relative: str, *, writing: bool = False) -> Path:
        candidate = (self.workspace / relative).resolve()
        if candidate != self.workspace and self.workspace not in candidate.parents:
            raise PermissionError("Path escapes task workspace.")
        if writing and candidate.suffix.lower() not in FILE_SUFFIXES:
            raise PermissionError("File type is outside first-release open-format support.")
        return candidate

    def search_web(self, query: str) -> dict[str, Any]:
        if not query.strip():
            raise ValueError("Search query is empty.")
        results: list[dict[str, str]] = []
        try:
            url = "https://lite.duckduckgo.com/lite/?" + urllib.parse.urlencode({"q": query[:250]})
            _, body = _fetch(url)
            parser = _DuckDuckGoResults()
            parser.feed(body)
            results = [{"title": item["title"].strip()[:250], "url": item["url"], "snippet": item["snippet"].strip()[:500]} for item in parser.results[:8]]
        except (ValueError, OSError):
            pass
        if not results:
            url = "https://www.bing.com/search?" + urllib.parse.urlencode({"q": query[:250], "format": "rss"})
            _, body = _fetch(url)
            root = ET.fromstring(body)
            for item in root.findall("./channel/item")[:8]:
                link = item.findtext("link", "")
                try:
                    _public_url(link)
                except ValueError:
                    continue
                results.append({
                    "title": item.findtext("title", "")[:250],
                    "url": link,
                    "snippet": html.unescape(item.findtext("description", ""))[:500],
                })
        return {"query": query, "results": results}

    def read_url(self, url: str, find: str = "") -> dict[str, Any]:
        final_url, body = _fetch(url, max_bytes=2_000_000)
        parser = _Text()
        parser.feed(body)
        content = " ".join(" ".join(parser.parts).split()) if "<" in body else body
        # HTML often splits API signatures across inline nodes. Restore the
        # punctuation spacing so a focused lookup such as csv.DictReader works.
        content = re.sub(r"(?<=\w)\.\s+(?=[A-Za-z_])", ".", content)
        content = re.sub(r"(?<=\w)\s+(?=\()", "", content)
        fragment = urllib.parse.unquote(urllib.parse.urlparse(url).fragment)
        actual_focus = find[:100]
        if find:
            position = content.casefold().find(find.casefold())
            if position < 0:
                raise ValueError(f"Find term absent from page: {find[:100]}")
            # The ledger retains a bounded leading excerpt. Keep the requested
            # section inside that excerpt rather than retaining only its preface.
            start = max(0, position - 200)
            excerpt = content[start:start + 12_000]
        elif fragment in parser.anchors:
            section = " ".join(parser.parts[parser.anchors[fragment]:])
            section = re.sub(r"(?<=\w)\.\s+(?=[A-Za-z_])", ".", section)
            section = re.sub(r"(?<=\w)\s+(?=\()", "", section)
            excerpt = section[:12_000]
            actual_focus = "#" + fragment[:100]
        else:
            excerpt = content[:12_000]
        result = {"url": final_url, "content": excerpt, "truncated": len(content) > len(excerpt), "focus": actual_focus}
        if result["truncated"] and not actual_focus:
            result["next_step_hint"] = "If the relevant section is absent, call read_url on this URL again with find set to a keyword."
        return result

    def list_files(self, path: str = ".") -> dict[str, Any]:
        root = self._path(path)
        if not root.exists() or not root.is_dir():
            raise FileNotFoundError(path)
        entries = []
        for child in sorted(root.iterdir())[:100]:
            if child.is_symlink():
                continue
            entries.append({"path": str(child.relative_to(self.workspace)), "type": "directory" if child.is_dir() else "file"})
        return {"entries": entries}

    def read_file(self, path: str) -> dict[str, Any]:
        target = self._path(path)
        if target.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("File exceeds reading limit.")
        return {"path": path, "content": target.read_text(encoding="utf-8")[:30_000]}

    def write_file(self, path: str, content: str) -> dict[str, Any]:
        target = self._path(path, writing=True)
        encoded = content.encode("utf-8")
        if len(encoded) > MAX_FILE_BYTES:
            raise ValueError("File exceeds writing limit.")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".aeon-tmp")
        temporary.write_bytes(encoded)
        temporary.replace(target)
        return {"path": str(target.relative_to(self.workspace)), "bytes": len(encoded)}

    def replace_text(self, path: str, old: str, new: str) -> dict[str, Any]:
        target = self._path(path, writing=True)
        if not target.is_file() or target.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("replace_text needs an existing supported text file within the size limit.")
        if not old:
            raise ValueError("replace_text needs non-empty old text.")
        content = target.read_text(encoding="utf-8")
        if content.count(old) != 1:
            raise ValueError("replace_text old text must occur exactly once; read the file and choose a unique excerpt.")
        result = self.write_file(path, content.replace(old, new, 1))
        return {**result, "replacements": 1}

    def create_site(self, spec: dict[str, Any]) -> dict[str, Any]:
        result = self.write_file("index.html", render_site(spec))
        return {**result, "design_palette": str(spec.get("palette", "amber"))}

    def run_check(self, check: str, path: str = ".") -> dict[str, Any]:
        target = self._path(path)
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm") or "npm"
        commands = {
            "python_tests": [sys.executable, "-m", "unittest", "discover"],
            "npm_build": [npm, "run", "build"],
            "npm_test": [npm, "test", "--", "--run"],
            "npm_install": [npm, "install", "--ignore-scripts"],
        }
        if check == "python_compile":
            if target.suffix != ".py":
                raise ValueError("python_compile needs a .py file.")
            command = [sys.executable, "-m", "py_compile", str(target)]
        elif check == "node_check":
            if target.suffix not in {".js", ".mjs"}:
                raise ValueError("node_check needs a JavaScript file.")
            command = ["node", "--check", str(target)]
        else:
            command = commands.get(check)
            if command is None:
                raise ValueError("Unsupported check.")
        from agent_lab.runner import sanitize_environment

        result = subprocess.run(
            command, cwd=self.workspace, env=sanitize_environment(), capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=120, shell=False, check=False,
        )
        return {"check": check, "returncode": result.returncode, "stdout": result.stdout[-5000:], "stderr": result.stderr[-3000:]}

    def _ensure_browser(self) -> None:
        if self._page:
            return
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as error:
            raise RuntimeError("Playwright is not installed; install the worker extra and Chromium.") from error
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=True, chromium_sandbox=os.environ.get("AEON_CHROMIUM_SANDBOX") == "1")
        self._context = self._browser.new_context(accept_downloads=False)
        def route_request(route):
            target_url = route.request.url
            try:
                self._guard_browser_request(target_url, method=route.request.method)
                route.continue_()
            except (ValueError, PermissionError):
                route.abort()
        self._context.route("**/*", route_request)
        self._page = self._context.new_page()

    def _guard_browser_request(self, target_url: str, *, method: str = "GET") -> None:
        parsed = urllib.parse.urlparse(target_url)
        if parsed.scheme == "file":
            local_path = Path(urllib.request.url2pathname(parsed.path)).resolve()
            if local_path != self.workspace and self.workspace not in local_path.parents:
                raise PermissionError("File URL escapes workspace.")
        elif parsed.scheme in {"http", "https"}:
            _public_url(target_url)
            if method.upper() not in {"GET", "HEAD", "OPTIONS"} and not self._write_guard_active:
                raise PermissionError("Browser read/preview cannot send an ungranted write request.")
            if self._write_guard_active and not _host_matches(parsed.hostname or "", self.grant.browser_write_domains):
                raise PermissionError("Browser write cannot request an ungranted domain.")
        elif parsed.scheme not in {"data", "blob"}:
            raise PermissionError("Unsupported browser URL scheme.")

    def inspect_site(self, path: str = "index.html") -> dict[str, Any]:
        target = self._path(path)
        if not target.is_file() or target.suffix.lower() != ".html":
            raise ValueError("inspect_site needs an existing HTML file in the workspace.")
        self._ensure_browser()
        assert self._page is not None
        issues: list[str] = []
        screenshots: list[str] = []
        console_errors: list[str] = []
        remote_requests: list[str] = []
        def on_error(error: Any) -> None:
            console_errors.append(str(error)[:300])
        def on_request(request: Any) -> None:
            if request.url.startswith(("http://", "https://")):
                remote_requests.append(request.url)
        self._page.on("pageerror", on_error)
        self._page.on("request", on_request)
        artifact_id = hashlib.sha256(path.encode("utf-8")).hexdigest()[:12]
        try:
            for name, width, height in (("desktop", 1440, 900), ("mobile", 390, 844)):
                self._page.set_viewport_size({"width": width, "height": height})
                self._page.goto(target.as_uri(), wait_until="load", timeout=20_000)
                self._page.wait_for_timeout(150)
                overflow = self._page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 2")
                if overflow:
                    issues.append(f"{name}: horizontal overflow")
                screenshot = self.evidence_dir / f"site-{artifact_id}-{name}.png"
                self._page.screenshot(path=str(screenshot), full_page=True)
                screenshots.append(str(screenshot))
        finally:
            self._page.remove_listener("pageerror", on_error)
            self._page.remove_listener("request", on_request)
        for form in self._page.locator("form").all()[:5]:
            handler = form.get_attribute("onsubmit") or ""
            if handler:
                import re

                match = re.search(r"^\s*(?:return\s+)?([A-Za-z_$][\w$]*)\s*\(", handler)
                if match and not self._page.evaluate("name => typeof window[name] === 'function'", match.group(1)):
                    issues.append(f"Form submit handler is undefined: {match.group(1)}")
        issues.extend("JavaScript error: " + error for error in console_errors[:5])
        return {"path": path, "title": self._page.title(), "issues": issues, "screenshots": screenshots,
                "remote_requests": sorted(set(remote_requests))}

    def browser(self, operation: str, *, url: str = "", selector: str = "", value: str = "", effect: str = "browser_write", amount: float = 0.0, recipient: str = "", cases: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        if operation == "test_local":
            if effect != "browser_write" or not isinstance(cases, list) or not 1 <= len(cases) <= 12:
                raise ValueError("test_local needs 1..12 cases and allows only local browser_write effects.")
            normalized_cases = []
            for case in cases:
                if not isinstance(case, dict) or not all(isinstance(case.get(key), str) for key in ("click", "expected")) or not case["expected"]:
                    raise ValueError("Each test needs click and nonempty expected strings.")
                fills = case.get("fills")
                if fills is None:
                    if not all(isinstance(case.get(key), str) for key in ("selector", "value")):
                        raise ValueError("Each test needs selector and value strings or a fills list.")
                else:
                    if not isinstance(fills, list) or not 1 <= len(fills) <= 12:
                        raise ValueError("fills needs 1..12 selector/value objects.")
                    parsed_fills = []
                    for item in fills:
                        if isinstance(item, str) and len(item) <= 512:
                            try:
                                item = json.loads(item)
                            except json.JSONDecodeError:
                                pass
                        if not isinstance(item, dict) or not isinstance(item.get("selector"), str) or not isinstance(item.get("value"), str):
                            raise ValueError("fills needs 1..12 selector/value objects.")
                        parsed_fills.append(item)
                    case = {**case, "fills": parsed_fills}
                normalized_cases.append(case)
            self.browser("navigate_local", url=url)
            checks = []
            for case in normalized_cases:
                # Reuse the guarded primitives; no JS evaluation or remote grant.
                for fill in case.get("fills", [{"selector": case.get("selector"), "value": case.get("value")} ]):
                    self.browser("fill", selector=fill["selector"], value=fill["value"])
                observed = self.browser("click", selector=case["click"])
                checks.append({**case, "operation": "click", "passed": case["expected"] in observed["text"], "observed_text": observed["text"][:2000]})
            return {"url": observed["url"], "title": observed["title"], "text": observed["text"], "checks": checks, "passed": all(case["passed"] for case in checks)}
        self._ensure_browser()
        assert self._page is not None
        if operation == "navigate":
            host = urllib.parse.urlparse(url).hostname or ""
            if self._write_guard_active and not _host_matches(host, self.grant.browser_write_domains):
                raise PermissionError("Browser session after a write is limited to granted domains; use read_url for other public sources.")
            self._page.goto(_public_url(url), wait_until="domcontentloaded", timeout=25_000)
        elif operation == "navigate_local":
            target = self._path(url)
            if not target.is_file() or target.suffix.lower() != ".html":
                raise ValueError("navigate_local requires an existing workspace HTML file.")
            self._page.goto(target.as_uri(), wait_until="load", timeout=20_000)
        elif operation == "screenshot":
            screenshot = self.evidence_dir / "browser-current.png"
            self._page.screenshot(path=str(screenshot), full_page=True)
            return {"url": self._page.url, "screenshot": str(screenshot)}
        elif operation in {"click", "fill"}:
            parsed = urllib.parse.urlparse(self._page.url)
            local = parsed.scheme == "file"
            if local:
                self._guard_browser_request(self._page.url)
                if effect != "browser_write":
                    raise PermissionError("Local interactions grant no external publish, message, delete, or spend action.")
            host = urllib.parse.urlparse(self._page.url).hostname or ""
            if not local and not _host_matches(host, self.grant.browser_write_domains):
                raise PermissionError("Browser write domain is not granted.")
            if not local and effect not in self.grant.external_actions:
                raise PermissionError(f"External action '{effect}' is not granted.")
            if effect == "message" and recipient not in self.grant.recipients:
                raise PermissionError("Message recipient is not granted.")
            if effect == "spend":
                if amount <= 0 or self.spent + amount > self.grant.max_spend:
                    raise PermissionError("Spend amount exceeds explicit task grant.")
            if not selector:
                raise ValueError("Browser selector is required.")
            if not local:
                self._write_guard_active = True
            locator = self._page.locator(selector).first
            if locator.count() == 0:
                controls = self._page.locator("input[id],button[id],select[id],textarea[id]").evaluate_all("els => els.map(el => '#' + el.id).slice(0, 20)")
                raise ValueError(f"Browser selector {selector!r} does not exist. Available control IDs: {controls}")
            if operation == "click":
                locator.click(timeout=10_000)
            else:
                if locator.evaluate("el => el.tagName.toLowerCase()") == "select":
                    options = locator.locator("option").evaluate_all("els => els.map(el => ({value: el.value, label: el.textContent.trim()}))")
                    chosen = next((item for item in options if value in {item["value"], item["label"]}), None)
                    if chosen is None:
                        raise ValueError(f"Select {selector!r} has no option {value!r}. Available options: {[item['label'] for item in options][:20]}")
                    locator.select_option(value=chosen["value"], timeout=10_000)
                else:
                    locator.fill(value, timeout=10_000)
            if effect == "spend" and operation == "click":
                self.spent += amount
        else:
            raise ValueError("Unknown browser operation.")
        return {"url": self._page.url, "title": self._page.title(), "text": self._page.locator("body").inner_text(timeout=10_000)[:6000]}

    def execute(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "search_web":
            return self.search_web(str(args.get("query", "")))
        if name == "read_url":
            return self.read_url(str(args.get("url", "")), str(args.get("find", "")))
        if name == "list_files":
            return self.list_files(str(args.get("path", ".")))
        if name == "read_file":
            return self.read_file(str(args.get("path", "")))
        if name == "write_file":
            return self.write_file(str(args.get("path", "")), str(args.get("content", "")))
        if name == "replace_text":
            return self.replace_text(str(args.get("path", "")), str(args.get("old", "")), str(args.get("new", "")))
        if name == "create_site":
            return self.create_site(args)
        if name == "run_check":
            return self.run_check(str(args.get("check", "")), str(args.get("path", ".")))
        if name == "inspect_site":
            return self.inspect_site(str(args.get("path", "index.html")))
        if name == "browser":
            return self.browser(
                str(args.get("operation", "")), url=str(args.get("url", "")),
                selector=str(args.get("selector", "")), value=str(args.get("value", "")),
                effect=str(args.get("effect", "browser_write")),
                amount=float(args.get("amount", 0)), recipient=str(args.get("recipient", "")),
                cases=args.get("cases"),
            )
        raise ValueError("Unknown tool.")
