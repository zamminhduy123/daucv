#!/usr/bin/env python3
"""Runner script for LLM #2 — CV Fit Evaluator & Judge.

Takes a CV (Canonical JSON or raw PDF/TXT) and a Job Description (file or text),
runs LLM #2 to evaluate candidate fit, and exports the structured evaluation report JSON.

Usage:
    python backend/scripts/run_llm2_evaluator.py --cv canonical_cv.json --jd job_description.txt --output fit_report.json

Or simply:
    python backend/scripts/run_llm2_evaluator.py
(and enter the file paths when prompted)
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

from app.services.cv_evaluator_service import evaluate_cv_fit
from app.services.cv_structuring_service import (
    structure_cv,
)
from app.services.layout_extraction import extract_cv_content_blocks

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("LLM2_Evaluator_Runner")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate a CV against a Job Description using LLM #2 (Fit Evaluator)."
    )
    parser.add_argument(
        "-c",
        "--cv",
        type=str,
        help="Path to CV file (canonical_cv.json, PDF, TXT, MD)",
        default=None,
    )
    parser.add_argument(
        "-j",
        "--jd",
        type=str,
        help="Path to Job Description file (.txt, .md) or raw JD text string",
        default=None,
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Path to save evaluation report JSON (default: fit_evaluation_report.json)",
        default="fit_evaluation_report.json",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    cv_input_str = args.cv
    jd_input_str = args.jd

    if not cv_input_str:
        print("\n=======================================================")
        print("        BÉ ĐẬU CV HELPER — LLM #2 EVALUATOR RUNNER     ")
        print("=======================================================\n")
        cv_input_str = input(
            "Enter path to CV file (canonical_cv.json, PDF, TXT): "
        ).strip()
        if not jd_input_str:
            jd_input_str = input(
                "Enter path to Job Description (optional - press Enter for General Audit): "
            ).strip()

    if not cv_input_str:
        logger.error("CV input file is required. Exiting.")
        sys.exit(1)

    cv_path = Path(cv_input_str).resolve()
    if not cv_path.exists():
        logger.error("CV file not found: %s", cv_path)
        sys.exit(1)

    output_path = Path(args.output).resolve()

    # 1. Load Canonical CV JSON (or run LLM #1 first if raw CV file provided)
    if cv_path.suffix.lower() == ".json":
        logger.info("Loading pre-mapped Canonical CV JSON: %s", cv_path)
        canonical_cv = json.loads(cv_path.read_text(encoding="utf-8"))
    else:
        logger.info(
            "Raw CV file provided (%s). Running LLM #1 Mapper first...", cv_path
        )
        if cv_path.suffix.lower() == ".pdf":
            pdf_bytes = cv_path.read_bytes()
            raw_extraction = extract_cv_content_blocks(pdf_bytes)
            cv_text = "\n".join(b.text for p in raw_extraction.pages for b in p.blocks)
        else:
            cv_text = cv_path.read_text(encoding="utf-8")

        structuring_res = await structure_cv(cv_text=cv_text)
        canonical_cv = structuring_res.document.to_canonical_dict()

    # 2. Load Job Description text (optional)
    job_description = None
    if jd_input_str and jd_input_str.strip():
        jd_path = Path(jd_input_str).resolve()
        if jd_path.exists():
            logger.info("Reading Job Description file: %s", jd_path)
            job_description = jd_path.read_text(encoding="utf-8")
        else:
            logger.info("Treating input as raw Job Description text string...")
            job_description = jd_input_str
    else:
        logger.info("No Job Description provided. Running in GENERAL CV AUDIT mode...")

    # 3. Run LLM #2 Evaluator
    logger.info("Running LLM #2 CV Fit Evaluator & Judge...")
    eval_result = await evaluate_cv_fit(
        canonical_cv=canonical_cv,
        job_description=job_description,
    )
    report = eval_result.report

    # Save output report
    output_dict = report.model_dump()
    output_path.write_text(
        json.dumps(output_dict, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Print summary
    print("\n" + "=" * 65)
    print("            LLM #2 CV FIT EVALUATION REPORT COMPLETE         ")
    print("=" * 65)
    print(f"Overall Fit Score : {report.overall_fit_score} / 100")
    print(f"Match Grade       : {report.match_grade}")
    print(f"Executive Summary : {report.executive_summary}\n")

    print("CATEGORY SUB-SCORES:")
    print(f"  • Technical Skills : {report.category_scores.technical_skills} / 100")
    print(f"  • Experience Level : {report.category_scores.experience_level} / 100")
    print(f"  • Domain Fit       : {report.category_scores.domain_fit} / 100")
    print(f"  • Education Fit    : {report.category_scores.education_fit} / 100\n")

    print("KEY STRENGTHS:")
    for s in report.key_strengths:
        print(f"  [✓] {s}")

    print("\nCRITICAL GAPS:")
    for g in report.critical_gaps:
        print(f"  [✗] {g}")

    print("\nSKILL MATRIX RECAP:")
    for item in report.skill_matrix[:5]:
        print(f"  • [{item.status.upper()}] {item.requirement}")
        if item.cv_evidence:
            print(f"      Evidence: {item.cv_evidence}")
        if item.gap_explanation:
            print(f"      Gap: {item.gap_explanation}")

    print("\nACTIONABLE RECOMMENDATIONS:")
    for r in report.actionable_recommendations:
        print(f"  [→] {r}")

    print("-" * 65)
    print(f"Saved full evaluation report JSON to: {output_path}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
