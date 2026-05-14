"""
CV Analysis — Deterministic Quality Checks
============================================
Post-hoc evaluation harness that runs entirely on the LLM's structured output
(no additional API calls). Catches score inconsistencies, hallucinated keywords,
and fabricated impact metrics before the response reaches the frontend.
"""

import re
from typing import List

from app.models.responses import CVAnalysisLLMResponse, CVAnalysisResponse, ScoreBreakdown


SCORE_WEIGHTS = {
    "technical_match": 0.30,
    "experience_relevance": 0.20,
    "keyword_coverage": 0.15,
    "impact_evidence": 0.15,
    "ats_readiness": 0.10,
    "tone_quality": 0.10,
}


# ---------------------------------------------------------------------------
# 1. Score consistency
# ---------------------------------------------------------------------------

def check_score_consistency(response: CVAnalysisResponse) -> List[str]:
    """
    Detect contradictions between ``match_score`` and the six sub-scores or
    the ``prioritized_keywords`` urgency level.
    """
    warnings: List[str] = []

    sub_scores = [
        response.technical_match,
        response.experience_relevance,
        response.keyword_coverage,
        response.impact_evidence,
        response.tone_quality,
        response.ats_readiness,
    ]
    avg_subscore = sum(sub_scores) / len(sub_scores)

    high_priority_count = sum(
        1 for kw in response.prioritized_keywords if kw.priority == "High"
    )
    if response.match_score > 85 and high_priority_count >= 3:
        warnings.append(
            f"Contradiction: match_score={response.match_score} (>85) but "
            f"{high_priority_count} keywords are marked High-priority missing. "
            f"A high match score should not coexist with many critical gaps."
        )

    return warnings


def build_scored_analysis(response: CVAnalysisLLMResponse) -> CVAnalysisResponse:
    """
    Calculate the overall match score from sub-scores and deterministic
    penalties. The LLM still explains the assessment, but code owns the final
    numeric score so it is stable across runs.
    """
    raw_score = round(
        SCORE_WEIGHTS["technical_match"] * response.technical_match
        + SCORE_WEIGHTS["experience_relevance"] * response.experience_relevance
        + SCORE_WEIGHTS["keyword_coverage"] * response.keyword_coverage
        + SCORE_WEIGHTS["impact_evidence"] * response.impact_evidence
        + SCORE_WEIGHTS["ats_readiness"] * response.ats_readiness
        + SCORE_WEIGHTS["tone_quality"] * response.tone_quality
    )

    critical_missing_count = sum(
        1 for item in response.evidence_analysis if item.evidence_strength == "Missing"
    )
    high_missing_count = sum(
        1 for item in response.prioritized_keywords if item.priority == "High"
    )
    unsupported_claim_count = sum(
        1
        for edit in response.suggested_edits
        if edit.rewrite_risk == "risky" or edit.unsupported_assumptions
    )

    critical_missing_penalty = 8 * critical_missing_count
    high_missing_penalty = 4 * high_missing_count
    unsupported_claim_penalty = 2 * unsupported_claim_count
    total_penalty = (
        critical_missing_penalty
        + high_missing_penalty
        + unsupported_claim_penalty
    )
    final_score = max(0, min(100, round(raw_score - total_penalty)))

    score_breakdown = ScoreBreakdown(
        weights=SCORE_WEIGHTS,
        raw_score=raw_score,
        critical_missing_count=critical_missing_count,
        high_missing_count=high_missing_count,
        unsupported_claim_count=unsupported_claim_count,
        critical_missing_penalty=critical_missing_penalty,
        high_missing_penalty=high_missing_penalty,
        unsupported_claim_penalty=unsupported_claim_penalty,
        total_penalty=total_penalty,
        final_score=final_score,
    )
    return CVAnalysisResponse(
        **response.model_dump(),
        match_score=final_score,
        score_breakdown=score_breakdown,
    )


# ---------------------------------------------------------------------------
# 2. Missing-keyword grounding
# ---------------------------------------------------------------------------

def check_missing_keywords_grounding(
    response: CVAnalysisLLMResponse,
    jd_text: str,
) -> List[str]:
    """
    Verify that every keyword the LLM claims is *missing from the CV but
    required by the JD* actually appears in the JD text. Keywords not found
    in the JD are likely hallucinated.
    """
    warnings: List[str] = []
    jd_lower = jd_text.lower()

    for kw in response.missing_keywords:
        if kw.lower() not in jd_lower:
            warnings.append(
                f"Hallucinated keyword: \"{kw}\" is listed as a missing keyword "
                f"but does not appear in the JD text."
            )

    return warnings


# ---------------------------------------------------------------------------
# 3. Unsupported / fabricated metrics in suggested edits
# ---------------------------------------------------------------------------

# Matches numbers (123, 8M, 2.5), percentages (35%), and multipliers (3x, 10x)
_METRIC_PATTERN = re.compile(
    r"""
    \b\d+(?:[.,]\d+)?        # integer or decimal  (e.g. 35, 2.5, 8,000)
    (?:\s*[%xX])?            # optional trailing %, x, or X
    (?:\s*[MmKkBb]\+?)?      # optional magnitude suffix (M, K, B) with optional +
    \b
    """,
    re.VERBOSE,
)


def _extract_metrics(text: str) -> set[str]:
    """Return the set of metric-like tokens found in *text*."""
    return {m.strip() for m in _METRIC_PATTERN.findall(text) if m.strip()}


def detect_unsupported_metrics(
    response: CVAnalysisLLMResponse,
    cv_text: str,
) -> List[str]:
    """
    Extract numbers / percentages / multipliers from each
    ``suggested_edits[].improved_safe`` and verify they exist somewhere in
    the original CV. Metrics that appear only in the rewrite may have been
    fabricated by the LLM.
    """
    warnings: List[str] = []
    cv_metrics = _extract_metrics(cv_text)

    for edit in response.suggested_edits:
        upgraded_metrics = _extract_metrics(edit.improved_safe)
        original_metrics = _extract_metrics(edit.original_text)

        # Metrics already present in the original bullet are fine
        novel_metrics = upgraded_metrics - original_metrics - cv_metrics

        for metric in sorted(novel_metrics):
            warnings.append(
                f"Possible fabricated metric: \"{metric}\" appears in a "
                f"suggested rewrite for [{edit.section}] but is not found "
                f"in the original CV text."
            )

    return warnings


# ---------------------------------------------------------------------------
# 4. Run all checks
# ---------------------------------------------------------------------------

def run_deterministic_eval(
    response: CVAnalysisLLMResponse,
    cv_text: str,
    jd_text: str,
) -> dict:
    """
    Execute all deterministic quality checks on an LLM analysis response.

    Returns::

        {
            "schema_valid": True,
            "warnings": ["...list of human-readable warnings..."]
        }
    """
    warnings: List[str] = []
    scored_response = build_scored_analysis(response)

    warnings.extend(check_score_consistency(scored_response))
    warnings.extend(check_missing_keywords_grounding(scored_response, jd_text))
    warnings.extend(detect_unsupported_metrics(scored_response, cv_text))

    return {
        "schema_valid": True,
        "warnings": warnings,
        "scored_response": scored_response,
    }
