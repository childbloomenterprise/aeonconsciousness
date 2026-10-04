"""Local UI acceptance checks; output contains no credentials."""

import json
import uuid
from pathlib import Path
from playwright.sync_api import sync_playwright

out = Path(__file__).resolve().parents[2] / "artifacts" / "enterprise-0.4.0"
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 960})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto("http://127.0.0.1:8787", wait_until="networkidle")
    page.get_by_role("button", name="+ New task").wait_for()
    page.wait_for_function(
        "() => document.querySelector('#role').textContent === 'owner'"
    )
    page.get_by_role("button", name="+ New task").click()
    title = "UI acceptance " + uuid.uuid4().hex[:8]
    page.get_by_label("Task name", exact=True).fill(title)
    page.get_by_label("Outcome and acceptance criteria").fill(
        "Create a short Markdown report with citations and verify each claim."
    )
    page.get_by_role("button", name="Queue task", exact=True).click()
    page.get_by_role("button", name="Open " + title).wait_for()
    page.get_by_role("button", name="Open " + title).click()
    page.wait_for_function(
        "() => document.querySelector('#dialog-body').textContent.includes('queued')"
    )
    page.get_by_role("button", name="Cancel task", exact=True).click()
    page.wait_for_function(
        "() => document.querySelector('#view').textContent.includes('cancelled')"
    )
    page.screenshot(path=str(out / "console-desktop.png"), full_page=True)
    for name in [
        "Workers",
        "Team & access",
        "Audit history",
        "Approvals",
        "Work queue",
    ]:
        page.get_by_role("button", name=name, exact=True).click()
        page.wait_for_timeout(150)
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=str(out / "console-mobile.png"), full_page=True)
    overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth")
    assert not overflow, "Mobile page overflows horizontally"
    assert not errors, errors
    (out / "browser-check.json").write_text(
        json.dumps(
            {
                "create_task": True,
                "task_details": True,
                "cancel_task": True,
                "navigation": True,
                "desktop": True,
                "mobile_no_overflow": not overflow,
                "page_errors": errors,
            },
            indent=2,
        )
    )
    browser.close()
print(
    "Browser acceptance: task creation, detail, cancellation, navigation, desktop/mobile passed."
)
