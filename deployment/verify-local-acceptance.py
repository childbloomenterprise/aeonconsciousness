"""Independent loopback acceptance: API downloads, hashes, and browser calculations."""
from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path, PurePosixPath
import urllib.request
import zipfile

from aeon_enterprise.local_service import call, local_origin
from aeon_enterprise.worker import SameOriginRedirect


def inspect_job(origin: str, job_id: str, output: Path) -> dict:
    detail = call(origin, f"/api/orgs/org_primary/jobs/{job_id}")
    job = detail["job"]
    download_root = output / "downloads" / job_id
    download_root.mkdir(parents=True, exist_ok=True)
    records = []
    opener = urllib.request.build_opener(SameOriginRedirect(origin))
    for artifact in detail["artifacts"]:
        relative = PurePosixPath(artifact["path"])
        if relative.is_absolute() or ".." in relative.parts or "\\" in artifact["path"]:
            raise ValueError("Unsafe returned artifact path")
        request = urllib.request.Request(
            origin + "/api/orgs/org_primary/artifacts/" + artifact["id"],
            headers={"Origin": origin},
        )
        with opener.open(request, timeout=20) as response:
            assert response.headers.get("Content-Disposition", "").startswith("attachment")
            payload = response.read(8_000_001)
        assert len(payload) <= 8_000_000
        digest = hashlib.sha256(payload).hexdigest()
        assert digest == artifact["sha256"]
        assert len(payload) == artifact["size"]
        target = download_root.joinpath(*relative.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        records.append({"path": artifact["path"], "size": len(payload), "sha256": digest})
    bundle = download_root / "deliverables.zip"
    if bundle.exists():
        with zipfile.ZipFile(bundle) as archive:
            assert archive.testzip() is None
            for record in records:
                if record["path"] == "deliverables.zip":
                    continue
                assert hashlib.sha256(archive.read(record["path"])).hexdigest() == record["sha256"]
    return {
        "job_id": job_id, "status": job["status"], "tokens": job["used_tokens"],
        "attempts": job["attempts"], "worker_id": job.get("worker_id"),
        "runtime_audit_valid": job.get("result", {}).get("audit_valid"),
        "unresolved_gaps": job.get("result", {}).get("unresolved_gaps"),
        "provider_route": job.get("result", {}).get("provider_route"),
        "artifacts": records, "download_hashes_verified": True,
        "bundle_verified": bundle.exists(), "download_root": str(download_root),
    }


def verify_tip(download_root: Path, output: Path) -> dict:
    from playwright.sync_api import sync_playwright

    page_path = download_root / "index.html"
    assert page_path.is_file()
    checks = []
    views = []
    errors = []
    requests = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("request", lambda request: requests.append(request.url))
            for name, width, height in [("desktop", 1440, 900), ("mobile", 375, 812)]:
                page.set_viewport_size({"width": width, "height": height})
                page.goto(page_path.as_uri())
                for amount, tip in [("100", "15"), ("0", "20"), ("40", "0"), ("12.50", "18")]:
                    page.locator("#amount").fill(amount)
                    page.locator("#tip").fill(tip)
                    page.locator("#calculate").click()
                    expected_tip = Decimal(amount) * Decimal(tip) / 100
                    expected_total = Decimal(amount) + expected_tip
                    observed_tip = page.locator("#tip-result").inner_text()
                    observed_total = page.locator("#total-result").inner_text()
                    assert Decimal(observed_tip) == expected_tip.quantize(Decimal("0.01"))
                    assert Decimal(observed_total) == expected_total.quantize(Decimal("0.01"))
                    assert not page.locator("#error").inner_text().strip()
                    checks.append({"viewport": name, "amount": amount, "tip": tip,
                                   "tip_result": observed_tip, "total_result": observed_total, "passed": True})
                for amount, tip in [("-1", "15"), ("100", "-1"), ("", "15")]:
                    page.locator("#amount").fill(amount)
                    page.locator("#tip").fill(tip)
                    page.locator("#calculate").click()
                    assert page.locator("#error").is_visible()
                    message = page.locator("#error").inner_text()
                    assert message.strip()
                    assert "NaN" not in page.locator(".results").inner_text()
                    if amount in {"-1", ""}:
                        assert Decimal(page.locator("#total-result").inner_text()) == 0
                    checks.append({"viewport": name, "amount": amount, "tip": tip, "error": message, "passed": True})
                page.locator("#amount").fill("200")
                page.locator("#tip").fill("15")
                page.locator("#tip").press("Enter")
                keyboard_enter = page.locator("#total-result").inner_text() == "230.00"
                page.locator("#calculate").click()
                assert page.locator("#total-result").inner_text() == "230.00"
                dimensions = page.evaluate("""() => ({width:innerWidth,
                    documentWidth:document.documentElement.scrollWidth,
                    buttonHeight:document.querySelector('#calculate').getBoundingClientRect().height,
                    labels:[...document.querySelectorAll('input')].every(e => !!document.querySelector('label[for="'+e.id+'"]'))})""")
                assert dimensions["documentWidth"] <= width
                assert dimensions["buttonHeight"] >= 44
                assert dimensions["labels"]
                screenshot = output / ("tip-" + name + ".png")
                page.screenshot(path=str(screenshot), full_page=True)
                views.append({"name": name, **dimensions, "screenshot": str(screenshot)})
        finally:
            browser.close()
    assert not errors, errors
    assert not any(url.startswith(("http:", "https:")) for url in requests), requests
    readme = (download_root / "README.md").read_text(encoding="utf-8")
    assert "index.html" in readme
    return {"checks": checks, "viewports": views, "javascript_errors": errors,
            "portable_no_external_requests": True, "keyboard_enter": keyboard_enter,
            "tested_file_sha256": hashlib.sha256(page_path.read_bytes()).hexdigest(),
            "visual_review": "screenshots saved; inspect independently"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--origin", default="http://127.0.0.1:8787")
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tip", action="store_true")
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()
    origin = local_origin(args.origin)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    result = inspect_job(origin, args.job_id, output)
    if args.tip:
        result["tip_acceptance"] = verify_tip(Path(result["download_root"]), output)
    (output / (args.job_id + "-acceptance.json")).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"job_id": args.job_id, "status": result["status"],
                      "artifacts": len(result["artifacts"]), "hashes_verified": True,
                      "tip_cases": len(result.get("tip_acceptance", {}).get("checks", []))}))
    if not args.allow_incomplete:
        assert result["status"] == "completed"
        assert result["runtime_audit_valid"] and not result["unresolved_gaps"]


if __name__ == "__main__":
    main()
