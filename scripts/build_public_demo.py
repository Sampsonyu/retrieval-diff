"""Assemble a static public demo from executed, checksum-verified case outputs."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build(output: Path) -> None:
    broken = ROOT / "artifacts/fastapi-docs"
    fixed = ROOT / "artifacts/fastapi-docs-fixed"
    measured = json.loads((broken / "measurements.json").read_text())
    corrected = json.loads((fixed / "measurements.json").read_text())
    report = json.loads((broken / "report.json").read_text())
    fixed_report = json.loads((fixed / "report.json").read_text())
    if measured["corpus_fingerprint"] != corrected["corpus_fingerprint"]:
        raise ValueError("Cannot publish comparisons across different corpora")
    if report["summary"]["gate"] != "fail" or fixed_report["summary"]["gate"] != "pass":
        raise ValueError("The demonstration must include a reproduced failure and corrected run")
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
    for source, target in (
        (broken / "report.html", "fastapi-regression.html"),
        (fixed / "report.html", "fastapi-fixed.html"),
        (ROOT / "artifacts/demo/report.html", "synthetic.html"),
    ):
        shutil.copyfile(source, output / "reports" / target)
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
