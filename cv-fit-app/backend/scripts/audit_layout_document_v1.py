#!/usr/bin/env python3
# ruff: noqa: E402
"""Audit offline LayoutDocumentV1 extraction and visual segmentation."""

import argparse
import json
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.layout_document_v1_service import (
    audit_span_conservation,
    extract_layout_document_v1,
    segment_visual_document,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit LayoutDocumentV1 for a PDF CV.")
    parser.add_argument("--input", "-i", required=True, help="PDF input")
    parser.add_argument("--output", "-o", default="layout_document_v1_audit.json")
    args = parser.parse_args()
    input_path = Path(args.input).resolve()
    if not input_path.exists():
        raise SystemExit(f"Input not found: {input_path}")
    document = extract_layout_document_v1(input_path.read_bytes())
    visual = segment_visual_document(document)
    audit = audit_span_conservation(document, visual)
    output_path = Path(args.output).resolve()
    output_path.write_text(
        json.dumps(
            {
                "layout_document": document.model_dump(mode="json"),
                "visual_document": visual.model_dump(mode="json"),
                "span_conservation": audit.model_dump(mode="json"),
                "passes": audit.passes,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"spans: {audit.source_span_count}; assigned: {audit.assigned_span_count}; ")
    print(
        f"missing: {len(audit.missing_span_ids)}; duplicates: {len(audit.duplicate_span_ids)}; passes: {audit.passes}"
    )
    print(f"audit JSON: {output_path}")


if __name__ == "__main__":
    main()
