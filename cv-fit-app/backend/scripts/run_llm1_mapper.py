#!/usr/bin/env python3
"""Runner script for LLM #1 — CV Mapper.

Takes a CV file path (PDF, TXT, MD), extracts raw blocks (Layer 1), passes them
to LLM #1 for semantic mapping (Layer 2), and exports the normalized canonical
CV JSON to an output file.

Usage:
    python backend/scripts/run_llm1_mapper.py --input path/to/cv.pdf --output path/to/output.json

Or simply:
    python backend/scripts/run_llm1_mapper.py
(and enter the file path when prompted)
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv

load_dotenv(backend_dir / ".env")

from app.services.cv_structuring_service import (
    build_manual_text_extraction,
    structure_cv,
)
from app.services.layout_extraction import extract_cv_content_blocks

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("LLM1_Mapper_Runner")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract and map a CV file into canonical normalized JSON using LLM #1."
    )
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        help="Path to input CV file (PDF, TXT, MD)",
        default=None,
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Path to save canonical CV JSON output (default: canonical_cv.json)",
        default="canonical_cv.json",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    input_path_str = args.input
    if not input_path_str:
        print("\n=======================================================")
        print("         BÉ ĐẬU CV HELPER — LLM #1 MAPPER RUNNER       ")
        print("=======================================================\n")
        input_path_str = input("Enter path to your CV file (PDF, TXT, MD): ").strip()

    if not input_path_str:
        logger.error("No input file path provided. Exiting.")
        sys.exit(1)

    input_path = Path(input_path_str).resolve()
    if not input_path.exists():
        logger.error("File not found: %s", input_path)
        sys.exit(1)

    output_path = Path(args.output).resolve()

    logger.info("Reading input CV file: %s", input_path)
    file_ext = input_path.suffix.lower()

    if file_ext == ".pdf":
        logger.info("Extracting raw blocks from PDF using layout engine...")
        pdf_bytes = input_path.read_bytes()
        raw_extraction = extract_cv_content_blocks(pdf_bytes)
        # Reconstruct text representation
        lines = [block.text for page in raw_extraction.pages for block in page.blocks]
        cv_text = "\n".join(lines)
    else:
        logger.info("Reading plain text file...")
        cv_text = input_path.read_text(encoding="utf-8")
        raw_extraction = build_manual_text_extraction(cv_text)

    logger.info(
        "Layer 1 complete: extracted %d total raw blocks.",
        sum(len(page.blocks) for page in raw_extraction.pages),
    )

    logger.info("Running LLM #1 Semantic CV Mapper...")
    structuring_result = await structure_cv(cv_text=cv_text)

    document = structuring_result.document
    canonical_json = document.to_canonical_dict()

    output_path.write_text(
        json.dumps(canonical_json, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n" + "=" * 60)
    print("           LLM #1 SEMANTIC CV MAPPING COMPLETE         ")
    print("=" * 60)
    print(f"Candidate Name : {canonical_json['identity'].get('name') or 'N/A'}")
    print(f"Headline       : {canonical_json['identity'].get('headline') or 'N/A'}")
    print(f"Email          : {canonical_json['identity'].get('email') or 'N/A'}")
    print(f"Education      : {len(canonical_json.get('education', []))} item(s)")
    print(f"Experience     : {len(canonical_json.get('experience', []))} item(s)")
    print(f"Skill Groups   : {len(canonical_json.get('skills', {}))} category(ies)")
    print(f"Publications   : {len(canonical_json.get('publications', []))} item(s)")
    print(f"Certifications : {len(canonical_json.get('certifications', []))} item(s)")
    print("-" * 60)
    print(f"Saved canonical CV JSON to: {output_path}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
