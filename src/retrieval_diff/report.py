"""Portable reports with no third-party assets or outbound requests."""

from __future__ import annotations

import html
import json
import re
from collections.abc import Sequence
from importlib.resources import files
from urllib.parse import urlsplit


def html_report(report: dict, *, navigation: Sequence[tuple[str, str]] = ()) -> str:
    # JSON lives in a non-executable script element. '<' must be escaped even
    # there: HTML parsers otherwise recognize user-supplied </script> sequences.
    payload = json.dumps(report, ensure_ascii=True, allow_nan=False).replace("<", "\\u003c")
    template = files("retrieval_diff").joinpath("report.html").read_text(encoding="utf-8")
    links = []
    for label, href in navigation:
        parsed = urlsplit(href)
        if (
            parsed.scheme not in ("", "https")
            or (parsed.netloc and not parsed.scheme)
            or "\\" in href
            or any(ord(c) < 32 for c in href)
            or href != href.strip()
            or (parsed.scheme == "https" and not parsed.netloc)
        ):
            raise ValueError("Navigation URLs must be relative paths or absolute HTTPS URLs")
        links.append(f'<a href="{html.escape(href, quote=True)}">{html.escape(label)}</a>')
    nav = (
        (
            '<nav class="report-navigation" aria-label="Report navigation">'
            + "".join(links)
            + "</nav>"
        )
        if links
        else ""
    )
    return re.sub(
        r"__REPORT_DATA__|__REPORT_NAV__",
        lambda match: payload if match[0] == "__REPORT_DATA__" else nav,
        template,
    )


def markdown_report(report: dict) -> str:
    def cell(value: str) -> str:
        # Raw HTML is escaped for Markdown viewers that allow it.
        import html

        return html.escape(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")

    s = report["summary"]
    lines = [
        "# Retrieval Diff",
        "",
        f"Gate: **{s['gate'].upper()}**",
        "",
        f"{s['queries']} queries · {s['labeled']} labeled · {s['regressed']} regressed",
        "",
        "| Query | Status | Recall before | Recall after | Lost sources |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for q in report["queries"]:
        bm, cm = q["baseline_metrics"], q["candidate_metrics"]
        b = f"{bm['document_recall']:.3f}" if bm is not None else "unlabeled"
        c = f"{cm['document_recall']:.3f}" if cm is not None else "unlabeled"
        lines.append(
            f"| {cell(q['query_id'])} | {q['status']} | {b} | {c} | "
            f"{cell(', '.join(q['lost_documents']))} |"
        )
    lines.extend(["", "## Interpretation", ""] + [f"- {w}" for w in report["warnings"]])
    return "\n".join(lines) + "\n"
