"""Regression checks for the core generated report, using the existing browser runner."""

import json
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright
from test_comparison import hit, snapshot

from retrieval_diff import compare
from retrieval_diff.report import html_report


def main():
    failures = []
    with sync_playwright() as p:
        executable = (
            shutil.which("chromium") if not Path(p.chromium.executable_path).exists() else None
        )
        browser = p.chromium.launch(executable_path=executable)

        def check(name, report, action):
            page = browser.new_page(viewport={"width": 390, "height": 844})
            page.set_content(html_report(report))
            try:
                action(page)
            except AssertionError as error:
                failures.append(name)
                print(f"FAIL {name}: {error}")
            finally:
                page.close()

        stable = compare(
            snapshot(hits=[hit("stable-source")], gold=("stable-source",)),
            snapshot(hits=[hit("stable-source")], gold=("stable-source",)),
        )

        def source_search(page):
            page.get_by_label("Search queries").fill(" stable-source ")
            assert page.locator(".query").count() == 1, "search loses unchanged sources"

        check("search unchanged source IDs", stable, source_search)

        missing = compare(
            snapshot(hits=[], gold=("missing-source",)), snapshot(hits=[], gold=("missing-source",))
        )

        def missing_source_search(page):
            page.get_by_label("Search queries").fill("missing-source")
            assert page.locator(".query").count() == 1, "search loses sources named in diagnostics"

        check("search missing source IDs from diagnostics", missing, missing_source_search)

        staged = compare(
            snapshot(
                stages=[{"name": "search", "hits": [hit()]}, {"name": "context", "hits": [hit()]}]
            ),
            snapshot(
                stages=[{"name": "search", "hits": [hit()]}, {"name": "context", "hits": [hit()]}]
            ),
        )

        def preserve_state(page):
            page.locator(".query > summary").click()
            page.get_by_label("BASELINE recorded stage").select_option("search")
            page.get_by_label("Search queries").fill("question")
            assert page.locator(".query").evaluate("node => node.open"), (
                "query collapsed while searching"
            )
            assert page.get_by_label("BASELINE recorded stage").input_value() == "search", (
                "stage selection reset"
            )
            page.get_by_role("button", name="BASELINE stage context (1 hits)", exact=True).click()
            assert page.get_by_label("BASELINE recorded stage").input_value() == "context", (
                "stage chip does not select its stage"
            )
            page.get_by_role("button", name="Source changes", exact=True).click()
            assert page.locator(".query").count() == 0
            page.get_by_role("button", name="All queries", exact=True).click()
            assert page.locator(".query").evaluate("node => node.open"), (
                "query state lost after filtering"
            )

        check("preserve expanded query and selected stage", staged, preserve_state)

        cutoff = compare(
            snapshot(hits=[hit("a"), hit("b")]), snapshot(hits=[hit("b"), hit("a")]), k=1
        )

        def cutoff_highlight(page):
            assert page.locator(".columns > div").nth(0).locator("code.lost").count() == 1, (
                "lost top-k source is not highlighted"
            )
            assert page.locator(".columns > div").nth(1).locator("code.gained").count() == 1
            assert page.get_by_text("Outside evaluation top-1", exact=True).count() == 2

        check("highlight evaluated top-k rather than all context", cutoff, cutoff_highlight)

        unlabeled = compare(snapshot(gold=None), snapshot(gold=None))

        def no_overflow(page):
            page.set_viewport_size({"width": 320, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (
                "unlabeled gate overflows mobile"
            )
            output = Path(__file__).resolve().parents[1] / "artifacts/bug-checks"
            output.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(output / "unlabeled-mobile.png"), full_page=True)

        check("unlabeled mobile report", unlabeled, no_overflow)
        browser.close()
    if failures:
        raise SystemExit(f"{len(failures)} report regressions: {json.dumps(failures)}")
    print(
        "Report regression checks passed: unchanged-source search, retained state, top-k highlights, unlabeled mobile layout."
    )


if __name__ == "__main__":
    main()
