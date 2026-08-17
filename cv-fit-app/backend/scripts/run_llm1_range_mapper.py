#!/usr/bin/env python3
# ruff: noqa: E402
"""Run isolated LLM #1 v3 range mapper; production routes remain unchanged."""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv

load_dotenv(backend_dir / ".env")

from app.services.cv_range_plan_service import structure_cv_range_plan
from app.services.cv_structuring_service import build_manual_text_extraction
from app.services.layout_extraction import extract_cv_content_blocks

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run isolated source-range CV mapper v3."
    )
    parser.add_argument("--input", "-i", required=True, help="PDF, TXT, or MD CV input")
    parser.add_argument("--output", "-o", default="canonical_cv_range_plan_v3.json")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    input_path = Path(args.input).resolve()
    if not input_path.exists():
        raise SystemExit(f"Input not found: {input_path}")
    if input_path.suffix.lower() == ".pdf":
        raw = extract_cv_content_blocks(input_path.read_bytes())
        cv_text = "\n".join(block.text for page in raw.pages for block in page.blocks)
    else:
        cv_text = input_path.read_text(encoding="utf-8")
        raw = build_manual_text_extraction(cv_text)
    result = await structure_cv_range_plan(cv_text=cv_text, raw_extraction=raw)
    output_path = Path(args.output).resolve()
    output_path.write_text(
        json.dumps(result.document.to_canonical_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        f"v3 atoms: {result.ledger_atom_count}; fallback: {result.used_fallback}; "
        f"unclassified atoms: {len(result.unclassified_atom_indexes)}; "
        f"section failures: {','.join(result.section_failures) or 'none'}; "
        f"export safe: {not result.document.requires_reprocessing}"
    )
    print(f"canonical JSON: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
