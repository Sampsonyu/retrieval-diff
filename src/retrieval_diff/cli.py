"""CLI exit codes: 0 comparison completed, 1 policy regression, 2 invalid input."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .compare import compare
from .model import Snapshot, ValidationError
from .report import html_report, markdown_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="retrieval-diff", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("validate", help="Validate a version-1 snapshot")
    check.add_argument("snapshot", type=Path)
    diff = commands.add_parser("compare", help="Compare matching snapshots and export reports")
    diff.add_argument("baseline", type=Path)
    diff.add_argument("candidate", type=Path)
    diff.add_argument("--k", type=int, default=5, help="Context chunk cutoff (default: 5)")
    diff.add_argument(
        "--max-recall-drop",
        type=float,
        default=0.0,
        help="Allowed absolute per-query document-recall drop (default: 0)",
    )
    diff.add_argument(
        "--max-mrr-drop", type=float, default=None, help="Opt into a per-query reciprocal-rank gate"
    )
    diff.add_argument(
        "--require-labels",
        action="store_true",
        help="Reject comparisons unless every query is labeled",
    )
    diff.add_argument("--html", type=Path, help="Write a self-contained interactive report")
    diff.add_argument("--json", type=Path, help="Write the machine-readable comparison")
    diff.add_argument("--markdown", type=Path, help="Write a Markdown summary")
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            snap = Snapshot.load(args.snapshot)
            print(f"Valid snapshot: {snap.run_id} ({len(snap.queries)} queries)")
            return 0
        inputs = {args.baseline.resolve(), args.candidate.resolve()}
        outputs = [p for p in (args.html, args.json, args.markdown) if p is not None]
        if len({p.resolve() for p in outputs}) != len(outputs):
            raise ValidationError("report output paths must be distinct")
        if any(p.resolve() in inputs for p in outputs):
            raise ValidationError("a report must not overwrite an input snapshot")
        report = compare(
            Snapshot.load(args.baseline),
            Snapshot.load(args.candidate),
            k=args.k,
            max_recall_drop=args.max_recall_drop,
            max_mrr_drop=args.max_mrr_drop,
        )
        s = report["summary"]
        if args.require_labels and s["labeled"] != s["queries"]:
            raise ValidationError("--require-labels requires relevance labels for every query")
        # Render everything before writing, so validation/render errors produce no reports.
        rendered = []
        for target, render in (
            (args.html, html_report),
            (args.json, lambda r: json.dumps(r, indent=2, allow_nan=False) + "\n"),
            (args.markdown, markdown_report),
        ):
            if target is not None:
                rendered.append((target, render(report)))
        for target, content in rendered:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        print(
            f"Gate: {s['gate'].upper()} | queries: {s['queries']} | labeled: {s['labeled']} | "
            f"regressed: {s['regressed']} | improved: {s['improved']}"
        )
        for q in report["queries"]:
            if q["status"] == "regressed":
                print(f"  REGRESSION {q['query_id']}: {', '.join(q['violations'])}")
        for warning in report["warnings"]:
            print(f"Note: {warning}", file=sys.stderr)
        return 1 if s["gate"] == "fail" else 0
    except (ValidationError, OSError, RecursionError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
