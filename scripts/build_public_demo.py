"""Assemble a static public demo from executed, checksum-verified case outputs."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from retrieval_diff import Snapshot, compare
from retrieval_diff.report import html_report

ROOT = Path(__file__).resolve().parents[1]


def build(output: Path) -> None:
    broken = ROOT / "artifacts/fastapi-docs"
    fixed = ROOT / "artifacts/fastapi-docs-fixed"
    measured = json.loads((broken / "measurements.json").read_text())
    corrected = json.loads((fixed / "measurements.json").read_text())
    report = compare(
        Snapshot.load(broken / "baseline.json"), Snapshot.load(broken / "candidate.json"), k=3
    )
    fixed_report = compare(
        Snapshot.load(fixed / "baseline.json"), Snapshot.load(fixed / "candidate.json"), k=3
    )
    if measured["corpus_fingerprint"] != corrected["corpus_fingerprint"]:
        raise ValueError("Cannot publish comparisons across different corpora")
    if report["summary"]["gate"] != "fail" or fixed_report["summary"]["gate"] != "pass":
        raise ValueError("The demonstration must include a reproduced failure and corrected run")
    for data, actual in ((measured, report), (corrected, fixed_report)):
        if data["summary"] != actual["summary"] or data["aggregate"] != actual["aggregate"]:
            raise ValueError(
                "Measurements do not match the recorded snapshots; rerun the experiment"
            )
    values = {
        "DOCS": measured["corpus_documents"],
        "CHUNKS": measured["chunks"],
        "QUERIES": measured["queries"],
        "REGRESSIONS": measured["summary"]["regressed"],
        "FIXED_REGRESSIONS": corrected["summary"]["regressed"],
        "BASE_RECALL": f"{measured['aggregate']['baseline']['document_recall']:.2f}",
        "CAND_RECALL": f"{measured['aggregate']['candidate']['document_recall']:.2f}",
        "FIXED_RECALL": f"{corrected['aggregate']['candidate']['document_recall']:.2f}",
    }
    html = (ROOT / "web/index.html").read_text()
    for key, value in values.items():
        html = html.replace(f"__{key}__", str(value))
    output.mkdir(parents=True, exist_ok=True)
    (output / "index.html").write_text(html)
    (output / "reports").mkdir(exist_ok=True)
    synthetic = compare(
        Snapshot.load(ROOT / "artifacts/demo/baseline.json"),
        Snapshot.load(ROOT / "artifacts/demo/candidate.json"),
        k=1,
    )
    reports = {
        "fastapi-regression.html": ("Failing public-docs run", report),
        "fastapi-fixed.html": ("Corrected public-docs run", fixed_report),
        "synthetic.html": ("Unchanged-average example", synthetic),
    }
    for target, (_, data) in reports.items():
        links = [("Demo overview", "../index.html")]
        links.extend(
            (label, filename) for filename, (label, _) in reports.items() if filename != target
        )
        (output / "reports" / target).write_text(
            html_report(data, navigation=links), encoding="utf-8"
        )
    (output / "data").mkdir(exist_ok=True)
    for source, target in (
        (broken / "measurements.json", "measurements.json"),
        (fixed / "measurements.json", "fixed-measurements.json"),
        (ROOT / "examples/fastapi_docs/corpus/sources.json", "sources.json"),
        (ROOT / "examples/fastapi_docs/queries.json", "queries.json"),
        (ROOT / "examples/fastapi_docs/corpus/FASTAPI_LICENSE", "FASTAPI_LICENSE"),
    ):
        shutil.copyfile(source, output / "data" / target)
    print(f"Built public demo: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/public-demo")
    args = parser.parse_args()
    build(args.output)
