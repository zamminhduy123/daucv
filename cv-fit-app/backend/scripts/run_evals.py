import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, TextIO


ROOT_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))


DEFAULT_CASES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]


def read_pair(case_id: int) -> tuple[str, str]:
    dataset_dir = ROOT_DIR / "dataset" / "golden"
    cv_path = dataset_dir / "cvs" / f"cv_{case_id:02d}.txt"
    jd_path = dataset_dir / "jds" / f"jd_{case_id:02d}.txt"

    if not cv_path.exists():
        raise FileNotFoundError(f"Missing CV fixture: {cv_path}")
    if not jd_path.exists():
        raise FileNotFoundError(f"Missing JD fixture: {jd_path}")

    return (
        cv_path.read_text(encoding="utf-8"),
        jd_path.read_text(encoding="utf-8"),
    )


def backend_modules() -> dict[str, Any]:
    try:
        from dotenv import load_dotenv

        load_dotenv(BACKEND_DIR / ".env")

        from app.models.responses import CVAnalysisLLMResponse
        from app.prompts.system_prompts import (
            CV_ANALYSIS_CONTEXT_WITH_JD,
            build_cv_analysis_prompt,
        )
        from app.services.ai_service import call_llm_with_fallback
        from app.services.cv_quality_checks import run_deterministic_eval
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Missing backend Python dependency. Run this with "
            "`backend/venv/bin/python run_evals.py` or install "
            "`backend/requirements.txt` into your active environment."
        ) from exc

    return {
        "CVAnalysisLLMResponse": CVAnalysisLLMResponse,
        "CV_ANALYSIS_CONTEXT_WITH_JD": CV_ANALYSIS_CONTEXT_WITH_JD,
        "build_cv_analysis_prompt": build_cv_analysis_prompt,
        "call_llm_with_fallback": call_llm_with_fallback,
        "run_deterministic_eval": run_deterministic_eval,
    }


async def analyze_case(case_id: int, output: TextIO = sys.stdout) -> None:
    modules = backend_modules()
    cv_text, jd_text = read_pair(case_id)
    system_prompt = modules["build_cv_analysis_prompt"](
        modules["CV_ANALYSIS_CONTEXT_WITH_JD"]
    )
    user_content = f"CV của ứng viên:\n{cv_text}\n\nMô tả Công việc (JD):\n{jd_text}"

    print(f"\n=== Case {case_id:02d} ===", file=output)

    try:
        response = await modules["call_llm_with_fallback"](
            system_prompt,
            user_content,
            modules["CVAnalysisLLMResponse"],
            feature_name="golden_dataset_eval",
            prompt_version="1.0.0",
            max_retries=1,
        )
    except Exception as exc:
        print(f"LLM call failed: {exc}", file=output)
        return

    eval_result = modules["run_deterministic_eval"](response, cv_text, jd_text)
    response = eval_result.scored_response

    # Save scored analysis to JSON file for evidence.
    analysis_dir = ROOT_DIR / "dataset" / "golden" / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    analysis_path = analysis_dir / f"analysis_{case_id:02d}.json"
    analysis_path.write_text(response.model_dump_json(indent=2), encoding="utf-8")

    warnings = eval_result.warnings

    print(f"match_score: {response.match_score}", file=output)
    print(f"headline: {response.match_headline}", file=output)
    print(f"eval_overall: {eval_result.overall}", file=output)
    print(f"warnings: {len(warnings)}", file=output)

    if not warnings:
        print("- No deterministic warnings.", file=output)
        return

    for warning in warnings:
        print(f"- {warning}", file=output)
    
    output.flush()



async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a few golden CV/JD fixtures through the LLM and print deterministic eval warnings."
    )
    parser.add_argument(
        "--cases",
        nargs="+",
        type=int,
        default=DEFAULT_CASES,
        help="Case numbers to evaluate. Defaults to 1 6 11 16 20.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all 20 cases in the golden dataset.",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Path to output file. If not provided, prints to console.",
    )
    args = parser.parse_args()

    case_list = list(range(1, 21)) if args.all else args.cases
    
    out_file = None
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_file = open(out_path, "w", encoding="utf-8")
        
        # Write header
        print(f"Evaluation Run: {datetime.now().isoformat()}", file=out_file)
        print(f"Cases: {case_list}", file=out_file)
        print("=" * 60, file=out_file)
    
    output_handle = out_file or sys.stdout

    try:
        for case_id in case_list:
            # Print progress to console even if logging to file
            if out_file:
                print(f"Processing Case {case_id:02d}...")
            await analyze_case(case_id, output_handle)
    finally:
        if out_file:
            print(f"\nEvaluation complete. Results saved to: {args.output}")
            out_file.close()


if __name__ == "__main__":
    asyncio.run(main())
