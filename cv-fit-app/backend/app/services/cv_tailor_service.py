"""LLM #3 orchestration for evidence-constrained canonical CV tailoring."""

from __future__ import annotations

import copy
import json
import logging
import re
from typing import Any

from pydantic import BaseModel

from app.models.cv_evaluation import LLMEvaluationReport
from app.models.cv_tailoring import (
    LLMTailoredCVResponse,
    TailoredCVResponse,
    TailoringChangeItem,
)
from app.prompts.system_prompts import build_cv_tailor_prompt
from app.services.ai_service import call_llm_with_fallback

logger = logging.getLogger(__name__)

_NUMBER_RE = re.compile(r"\b\d+(?:[.,]\d+)?(?:\s*[%xX])?(?:[MmKkBb]\+?)?\b")
_TAILOR_MAX_OUTPUT_TOKENS = 768


class TailoringResult(BaseModel):
    """Result container for a canonical CV tailoring operation."""

    response: TailoredCVResponse
    raw_prompt: str | None = None
    provider_used: str | None = None


_DIGIT_CLAIM_RE = re.compile(r"\d+(?:[.,]\d+)?")


def _numeric_claims(text: str) -> set[str]:
    """Extract normalized numeric values from text to prevent metric fabrication."""
    return {re.sub(r"[,\s]", "", m) for m in _DIGIT_CLAIM_RE.findall(text)}


def _has_matching_shape(source: Any, tailored: Any) -> bool:
    """Require mappings, lists, and scalar types to retain their CV structure."""
    if type(source) is not type(tailored):
        return False
    if isinstance(source, dict):
        return set(source) == set(tailored) and all(
            _has_matching_shape(source[key], tailored[key]) for key in source
        )
    if isinstance(source, list):
        return len(source) == len(tailored) and all(
            _has_matching_shape(source_item, tailored_item)
            for source_item, tailored_item in zip(source, tailored, strict=True)
        )
    return True


_BULLET_PATH_RE = re.compile(
    r"^(experience|research_experience|projects)\[(\d+)\]\.bullets\[(\d+)\]\.text$"
)


def _resolve_mutable_text_path(cv: dict[str, Any], path: str) -> tuple[Any, str | int]:
    """Return the mutable container/key for a narrow allowlist of text fields."""
    bullet_match = _BULLET_PATH_RE.fullmatch(path)
    if bullet_match:
        section, entry_index, bullet_index = bullet_match.groups()
        try:
            entry = cv[section][int(entry_index)]
            bullet = entry["bullets"][int(bullet_index)]
        except (IndexError, KeyError, TypeError) as exc:
            raise ValueError(f"Unknown tailoring path: {path}") from exc
        if isinstance(bullet, dict) and isinstance(bullet.get("text"), str):
            return bullet, "text"
        if isinstance(bullet, str):
            return entry["bullets"], int(bullet_index)
        raise ValueError(f"Unknown tailoring path: {path}")

    raise ValueError(f"Unsupported tailoring path: {path}")


def _apply_tailoring_operations(
    source_cv: dict[str, Any],
    llm_response: LLMTailoredCVResponse,
) -> TailoredCVResponse:
    """Apply only safe text rewrites; reject bad individual operations locally.

    LLM #3 is allowed to suggest at most two independent edits. One invalid
    suggestion must not turn an otherwise useful/no-op response into a 503.
    The server therefore drops only that operation and never applies it.
    """
    tailored_cv = copy.deepcopy(source_cv)
    applied_changes: list[TailoringChangeItem] = []
    seen_paths: set[str] = set()
    rejected_count = 0
    for operation in llm_response.change_log:
        if operation.path in seen_paths:
            logger.warning("Discarded duplicate LLM #3 operation at %s", operation.path)
            rejected_count += 1
            continue
        seen_paths.add(operation.path)
        try:
            container, key = _resolve_mutable_text_path(tailored_cv, operation.path)
        except ValueError:
            logger.warning(
                "Discarded unsupported LLM #3 operation path: %s", operation.path
            )
            rejected_count += 1
            continue
        original_text = container[key]
        proposed_numbers = _numeric_claims(operation.proposed_text)
        original_numbers = _numeric_claims(original_text)
        if not proposed_numbers.issubset(original_numbers):
            logger.warning(
                "Discarded LLM #3 operation with invented numeric evidence at %s (proposed: %s, original: %s)",
                operation.path,
                proposed_numbers,
                original_numbers,
            )
            rejected_count += 1
            continue
        if not original_numbers.issubset(proposed_numbers):
            logger.warning(
                "Discarded LLM #3 operation with removed numeric evidence at %s (proposed: %s, original: %s)",
                operation.path,
                proposed_numbers,
                original_numbers,
            )
            rejected_count += 1
            continue
        if operation.proposed_text.strip() == original_text.strip():
            continue
        container[key] = operation.proposed_text
        applied_changes.append(
            TailoringChangeItem(
                path=operation.path,
                proposed_text=operation.proposed_text,
                rationale=operation.rationale,
                original_text=original_text,
            )
        )

    if not _has_matching_shape(source_cv, tailored_cv):
        raise ValueError("Tailored CV must preserve the canonical CV data shape")
    tailoring_summary = llm_response.tailoring_summary
    if rejected_count and not applied_changes:
        tailoring_summary = "No safe CV changes were applied; the proposed rewrite changed protected evidence."
    return TailoredCVResponse(
        tailored_cv=tailored_cv,
        change_log=applied_changes,
        tailoring_summary=tailoring_summary,
    )


async def tailor_cv(
    canonical_cv: dict[str, Any],
    job_description: str | None = None,
    evaluation: LLMEvaluationReport | dict[str, Any] | None = None,
) -> TailoringResult:
    """Tailor a canonical CV, with or without a job description, without adding facts.

    The returned JSON keeps LLM #1's canonical shape.  A small deterministic
    guard discards operations that change protected numeric claims or target an
    unsupported field; semantic factual grounding remains an LLM #3 instruction.
    """
    if not canonical_cv:
        raise ValueError("canonical_cv is required")
    normalized_jd = (
        job_description.strip() if job_description and job_description.strip() else None
    )

    evaluation_payload: dict[str, Any] | None
    if isinstance(evaluation, LLMEvaluationReport):
        evaluation_payload = evaluation.model_dump(mode="json")
    else:
        evaluation_payload = evaluation

    job_description_section = (
        f"=== JOB DESCRIPTION ===\n{normalized_jd}\n\n"
        if normalized_jd
        else "=== JOB DESCRIPTION ===\nNot supplied. Perform a general CV enhancement audit.\n\n"
    )
    user_prompt = (
        "=== CANONICAL CV JSON ===\n"
        f"{json.dumps(canonical_cv, ensure_ascii=False, indent=2)}\n\n"
        f"{job_description_section}"
        "=== LLM #2 EVALUATION (OPTIONAL) ===\n"
        f"{json.dumps(evaluation_payload, ensure_ascii=False, indent=2) if evaluation_payload else 'Not supplied'}\n\n"
        "Return a strict LLMTailoredCVResponse JSON containing only a short change_log and tailoring_summary."
    )
    logger.info("Running LLM #3 canonical CV tailor")
    response = await call_llm_with_fallback(
        system_prompt=build_cv_tailor_prompt(has_jd=bool(normalized_jd)),
        user_input=user_prompt,
        response_model=LLMTailoredCVResponse,
        feature_name="cv_tailoring",
        max_output_tokens=_TAILOR_MAX_OUTPUT_TOKENS,
    )
    response = LLMTailoredCVResponse.model_validate(response)
    tailored_response = _apply_tailoring_operations(canonical_cv, response)
    return TailoringResult(
        response=tailored_response,
        raw_prompt=user_prompt,
        provider_used="LLM_Router",
    )
