"""Optional browser checks. Install Playwright separately; not a runtime dependency.

Run from the repository root: python tests/browser_smoke.py
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright

from retrieval_diff import Snapshot, compare
from retrieval_diff.report import html_report


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    artifacts = root / "artifacts/demo"
    report_path = artifacts / "report.html"
    assert report_path.exists(), "Run the README demo first."
    baseline = Snapshot.load(artifacts / "baseline.json")
    raw = baseline.to_dict()
    # Use JSON to normalize tuples before editing the untrusted-data fixture.
    raw = json.loads(json.dumps(raw))
    attack = '</script><script>window.injected=true</script><img src="https://example.com/attack">'
    for stage in raw["queries"][0]["stages"]:
        for hit in stage["hits"]:
            hit["text"] = attack
    unsafe_snapshot = Snapshot.from_dict(raw)
    unsafe_report = artifacts / "untrusted-input.html"
    unsafe_report.write_text(
        html_report(compare(unsafe_snapshot, unsafe_snapshot)), encoding="utf-8"
    )

    with sync_playwright() as p:
        system_chromium = (
            shutil.which("chromium") if not Path(p.chromium.executable_path).exists() else None
        )
        browser = p.chromium.launch(executable_path=system_chromium)
        page = browser.new_page(viewport={"width": 1365, "height": 1050}, device_scale_factor=1)
        errors, outbound = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "request",
            lambda request: (
                outbound.append(request.url)
                if request.url.startswith(("http://", "https://"))
                else None
            ),
        )
        page.set_content(report_path.read_text(encoding="utf-8"))
        page.locator(".query").first.wait_for()
        assert page.locator(".query").count() == 4
        assert "0.750 → 0.750" in page.locator("#aggregate").inner_text()
        page.get_by_role("button", name="Regressions", exact=True).click()
        assert page.locator(".query").count() == 1
        assert "legacy-retention" in page.locator(".query").inner_text()
        assert "status=legacy excluded" in page.locator(".diagnosis").inner_text()
        page.get_by_label("CANDIDATE recorded stage").select_option("search")
        assert "legacy-exports" in page.locator(".columns > div").nth(1).inner_text()
        page.get_by_label("CANDIDATE recorded stage").select_option("context")
        page.get_by_role("button", name="All queries", exact=True).click()
        page.get_by_label("Search queries").fill("sso")
        assert page.locator(".query").count() == 1
        page.get_by_label("Search queries").fill("not-a-real-question")
        assert page.get_by_text("No matching queries.").is_visible()
        page.get_by_label("Search queries").fill("")
        page.screenshot(path=str(artifacts / "report-desktop.png"), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=str(artifacts / "report-mobile.png"), full_page=True)
        page = browser.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "request",
            lambda request: (
                outbound.append(request.url)
                if request.url.startswith(("http://", "https://"))
                else None
            ),
        )
        page.set_content(unsafe_report.read_text(encoding="utf-8"))
        page.locator(".query").first.locator("summary").click()
        assert page.evaluate("window.injected === undefined")
        assert page.locator("img").count() == 0
        assert attack in page.locator(".query").first.inner_text()
        assert not errors, errors
        assert not outbound, outbound
        browser.close()
    print(
        "Browser checks passed: filters, search, stage selection, mobile layout, untrusted text, zero outbound requests."
    )


if __name__ == "__main__":
    main()
