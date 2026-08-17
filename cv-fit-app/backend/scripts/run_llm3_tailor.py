#!/usr/bin/env python3
"""Run LLM #3 to tailor a canonical CV JSON to a target job description."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Tailor canonical CV JSON with LLM #3."
    )
    parser.add_argument("--cv", required=True, help="Path to canonical CV JSON")
    parser.add_argument(
        "--jd",
        help="Optional path to target JD text, or a raw JD string",
    )
    parser.add_argument("--evaluation", help="Optional LLM #2 evaluation JSON")
    parser.add_argument("--output", default="tailored_cv.json", help="Output JSON path")
    return parser.parse_args()


# .venv/bin/python backend/scripts/run_llm3_tailor.py --cv canonical_cv.json --output fit_evaluation_report.json


async def main() -> None:
    from dotenv import load_dotenv

    load_dotenv(backend_dir / ".env")
    from app.models.cv_evaluation import LLMEvaluationReport
    from app.services.cv_tailor_service import tailor_cv

    args = parse_args()
    canonical_cv = json.loads(Path(args.cv).read_text(encoding="utf-8"))
    jd_path = Path(args.jd) if args.jd else None
    job_description = (
        jd_path.read_text(encoding="utf-8") if jd_path and jd_path.exists() else args.jd
    )
    evaluation = (
        LLMEvaluationReport.model_validate_json(
            Path(args.evaluation).read_text(encoding="utf-8")
        )
        if args.evaluation
        else None
    )
    result = await tailor_cv(canonical_cv, job_description, evaluation)
    Path(args.output).write_text(
        json.dumps(result.response.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Saved tailored CV and change log to: {Path(args.output).resolve()}")


if __name__ == "__main__":
    asyncio.run(main())
