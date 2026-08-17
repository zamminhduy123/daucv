#!/usr/bin/env python3
# ruff: noqa: E402
"""Run experimental LLM #1 v2 without changing the production mapper."""

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

from app.services.cv_block_plan_service import structure_cv_block_plan
from app.services.cv_structuring_service import (
    build_manual_text_extraction,
)
from app.services.layout_extraction import extract_cv_content_blocks

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run isolated source-atom CV mapper v2."
    )
    parser.add_argument("--input", "-i", required=True, help="PDF, TXT, or MD CV input")
    parser.add_argument("--output", "-o", default="canonical_cv_block_plan_v2.json")
    parser.add_argument(
        "--plan-output", default=None, help="Optional raw LLM plan JSON path"
    )
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
    result = await structure_cv_block_plan(cv_text=cv_text, raw_extraction=raw)
    output_path = Path(args.output).resolve()
    output_path.write_text(
        json.dumps(result.document.to_canonical_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if args.plan_output and result.plan:
        Path(args.plan_output).resolve().write_text(
            result.plan.model_dump_json(indent=2), encoding="utf-8"
        )
    print(
        "v2 atoms: "
        f"{result.atom_count}; fallback: {result.used_fallback}; "
        f"repeated atoms: {len(result.repeated_atom_ids)}; "
        f"unknown atoms: {len(result.unknown_atom_ids)}; "
        f"missing atoms: {len(result.missing_atom_ids)}; "
        f"section fallbacks: {','.join(result.section_fallback_types) or 'none'}; "
        f"export safe: {not result.document.requires_reprocessing}"
    )
    print(f"canonical JSON: {output_path}")
    if args.plan_output and result.plan:
        print(f"plan JSON: {Path(args.plan_output).resolve()}")


if __name__ == "__main__":
    asyncio.run(main())
