"""
CV Analysis — Deterministic Quality Checks
============================================
Post-hoc evaluation harness that runs entirely on the LLM's structured output
(no additional API calls). Catches score inconsistencies, hallucinated keywords,
and fabricated impact metrics before the response reaches the frontend.
"""

import re
from typing import List

from pydantic import BaseModel, Field

from app.models.responses import CVAnalysisLLMResponse, CVAnalysisResponse, ScoreBreakdown


SCORE_WEIGHTS = {
    "technical_match": 0.30,
    "experience_relevance": 0.20,
    "keyword_coverage": 0.15,
    "impact_evidence": 0.15,
    "ats_readiness": 0.10,
    "tone_quality": 0.10,
}

PRIORITY_WEIGHTS = {
    "Critical": 12,
    "High": 8,
    "Medium": 4,
    "Low": 2,
}

_STOPWORDS = {
    "and", "or", "the", "for", "with", "from", "into", "that", "this", "you",
    "your", "are", "can", "will", "must", "need", "needs", "using", "use",
    "job", "role", "skill", "skills", "experience", "knowledge",
}


class EvalResult(BaseModel):
    schema_valid: bool = True
    score_consistency: int = Field(ge=0, le=100)
    explicit_jd_keyword_accuracy: int = Field(ge=0, le=100)
    semantic_keyword_usefulness: int = Field(ge=0, le=100)
    cv_grounding: int = Field(ge=0, le=100)
    truthfulness: int = Field(ge=0, le=100)
    placeholder_handling: int = Field(ge=0, le=100)
    rewrite_safety: int = Field(ge=0, le=100)
    actionability: int = Field(ge=0, le=100)
    overall: int = Field(ge=0, le=100)
    warnings: List[str]
    hard_hallucinations: List[str]
    soft_inferences: List[str]
    useful_adjacent_recommendations: List[str]
    placeholder_metrics: List[str]
    unsupported_factual_claims: List[str]
    needs_user_confirmation: List[str]
    scored_response: CVAnalysisResponse


def _clamp_score(value: int) -> int:
    return max(0, min(100, value))


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]*", text.lower())
        if len(token) > 2 and token not in _STOPWORDS
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

    critical_missing_count = sum(
        1 for kw in response.prioritized_keywords if kw.priority == "Critical"
    )
    high_missing_count = sum(
        1 for kw in response.prioritized_keywords if kw.priority == "High"
    )
    missing_penalty = response.score_breakdown.weighted_missing_requirement_score

    if response.match_score >= 85 and critical_missing_count >= 1:
        warnings.append(
            f"High score despite missing critical JD requirement: "
            f"match_score={response.match_score}, critical_missing_count={critical_missing_count}."
        )

    if response.match_score >= 85 and missing_penalty >= 20:
        warnings.append(
            f"High score despite high weighted missing-requirement penalty: "
            f"match_score={response.match_score}, missing_penalty={missing_penalty}."
        )

    if response.keyword_coverage >= 80 and high_missing_count >= 3:
        warnings.append(
            f"Keyword coverage score too high for high-priority gaps: "
            f"keyword_coverage={response.keyword_coverage}, high_missing_count={high_missing_count}."
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
        1 for item in response.prioritized_keywords if item.priority == "Critical"
    )
    high_missing_count = sum(
        1 for item in response.prioritized_keywords if item.priority == "High"
    )
    weighted_missing_requirement_score = sum(
        PRIORITY_WEIGHTS[item.priority] for item in response.prioritized_keywords
    )
    unsupported_claim_count = sum(
        1
        for edit in response.suggested_edits
        if edit.rewrite_risk == "risky" or edit.unsupported_assumptions
    )

    critical_missing_penalty = 12 * critical_missing_count
    high_missing_penalty = 8 * high_missing_count
    missing_requirement_penalty = weighted_missing_requirement_score
    unsupported_claim_penalty = 2 * unsupported_claim_count
    total_penalty = (
        missing_requirement_penalty
        + unsupported_claim_penalty
    )
    final_score = max(0, min(100, round(raw_score - total_penalty)))

    score_breakdown = ScoreBreakdown(
        weights=SCORE_WEIGHTS,
        raw_score=raw_score,
        critical_missing_count=critical_missing_count,
        high_missing_count=high_missing_count,
        weighted_missing_requirement_score=weighted_missing_requirement_score,
        unsupported_claim_count=unsupported_claim_count,
        critical_missing_penalty=critical_missing_penalty,
        high_missing_penalty=high_missing_penalty,
        missing_requirement_penalty=missing_requirement_penalty,
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

def classify_keyword_grounding(
    response: CVAnalysisLLMResponse,
    jd_text: str,
) -> dict[str, List[str]]:
    """
    Classify keyword issues more carefully than "not in JD = hallucination".

    - Exact JD terms are accepted.
    - Terms with lexical overlap are treated as soft inferences.
    - Medium/Low priority terms without direct JD grounding are treated as
      adjacent recommendations, not missing requirements.
    - High/Critical ungrounded terms are hard hallucinations because they are
      presented as important missing JD requirements.
    """
    jd_lower = _normalize(jd_text)
    jd_tokens = _tokens(jd_text)
    priority_by_keyword = {
        _normalize(item.keyword): item.priority for item in response.prioritized_keywords
    }

    result = {
        "hard_hallucinations": [],
        "soft_inferences": [],
        "useful_adjacent_recommendations": [],
    }

    seen_keywords = set(response.missing_keywords)
    seen_keywords.update(item.keyword for item in response.prioritized_keywords)

    for keyword in sorted(seen_keywords):
        normalized_keyword = _normalize(keyword)
        if normalized_keyword in jd_lower:
            continue

        priority = priority_by_keyword.get(normalized_keyword)
        keyword_tokens = _tokens(keyword)
        overlap = keyword_tokens & jd_tokens

        if overlap:
            result["soft_inferences"].append(
                f"{keyword}: not an exact JD phrase, but semantically connected via {sorted(overlap)}."
            )
        elif priority in {"Medium", "Low"}:
            result["useful_adjacent_recommendations"].append(
                f"{keyword}: not in the JD, but acceptable as an adjacent recommendation if labeled as optional/true."
            )
        else:
            result["hard_hallucinations"].append(
                f"{keyword}: presented as a missing JD requirement but no exact or semantic JD grounding was found."
            )

    return result


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


def classify_rewrite_grounding(
    response: CVAnalysisLLMResponse,
    cv_text: str,
) -> dict[str, List[str]]:
    """
    Extract numbers / percentages / multipliers from each
    ``suggested_edits[].improved_safe`` and classify unsupported claims.
    Placeholder metrics in ``improved_with_placeholders`` are expected and safe
    when they remain bracketed.
    """
    unsupported_factual_claims: List[str] = []
    placeholder_metrics: List[str] = []
    needs_user_confirmation: List[str] = []
    cv_metrics = _extract_metrics(cv_text)

    for edit in response.suggested_edits:
        safe_metrics = _extract_metrics(edit.improved_safe)
        original_metrics = _extract_metrics(edit.original_text)

        # Metrics already present in the original bullet are fine
        novel_metrics = safe_metrics - original_metrics - cv_metrics

        for metric in sorted(novel_metrics):
            unsupported_factual_claims.append(
                f"{edit.section}: metric \"{metric}\" appears in improved_safe but is not found in the original CV."
            )

        placeholders = re.findall(r"\[[^\]]+\]", edit.improved_with_placeholders)
        for placeholder in placeholders:
            if _extract_metrics(placeholder) or any(
                token in placeholder.lower()
                for token in ("%", "before", "after", "user", "workflow", "request", "latency")
            ):
                placeholder_metrics.append(f"{edit.section}: {placeholder}")

        for assumption in edit.unsupported_assumptions:
            needs_user_confirmation.append(f"{edit.section}: {assumption}")

    return {
        "unsupported_factual_claims": unsupported_factual_claims,
        "placeholder_metrics": placeholder_metrics,
        "needs_user_confirmation": needs_user_confirmation,
    }


def detect_unsupported_metrics(
    response: CVAnalysisLLMResponse,
    cv_text: str,
) -> List[str]:
    """Backward-compatible wrapper for older tests/scripts."""
    return classify_rewrite_grounding(response, cv_text)["unsupported_factual_claims"]


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

    Returns a rich EvalResult. It still exposes ``warnings`` for existing eval
    scripts, but separates hard issues from allowed controlled inference.
    """
    scored_response = build_scored_analysis(response)
    score_warnings = check_score_consistency(scored_response)
    keyword_result = classify_keyword_grounding(scored_response, jd_text)
    rewrite_result = classify_rewrite_grounding(scored_response, cv_text)

    hard_hallucinations = keyword_result["hard_hallucinations"]
    soft_inferences = keyword_result["soft_inferences"]
    useful_adjacent_recommendations = keyword_result["useful_adjacent_recommendations"]
    placeholder_metrics = rewrite_result["placeholder_metrics"]
    unsupported_factual_claims = rewrite_result["unsupported_factual_claims"]
    needs_user_confirmation = rewrite_result["needs_user_confirmation"]

    warnings = [
        *score_warnings,
        *hard_hallucinations,
        *unsupported_factual_claims,
    ]

    explicit_keyword_total = len(response.missing_keywords) or 1
    explicit_jd_keyword_accuracy = _clamp_score(
        100 - round(100 * len(hard_hallucinations) / explicit_keyword_total)
    )
    semantic_keyword_usefulness = _clamp_score(
        100 - 5 * len(hard_hallucinations) + 2 * len(soft_inferences)
    )
    truthfulness = _clamp_score(
        100 - 30 * len(hard_hallucinations) - 25 * len(unsupported_factual_claims)
    )
    placeholder_handling = _clamp_score(
        100 if placeholder_metrics else 80 - 10 * len(unsupported_factual_claims)
    )
    rewrite_safety = _clamp_score(
        100 - 25 * len(unsupported_factual_claims) - 10 * sum(
            1 for edit in response.suggested_edits if edit.rewrite_risk == "risky"
        )
    )
    score_consistency = _clamp_score(100 - 20 * len(score_warnings))
    cv_grounding = _clamp_score(
        100 - 25 * len(unsupported_factual_claims) - 15 * len(hard_hallucinations)
    )
    actionability = _clamp_score(
        70 + 5 * len(response.suggested_edits) + 3 * len(needs_user_confirmation)
    )
    overall = _clamp_score(round(
        0.15 * score_consistency
        + 0.12 * explicit_jd_keyword_accuracy
        + 0.10 * semantic_keyword_usefulness
        + 0.15 * cv_grounding
        + 0.18 * truthfulness
        + 0.10 * placeholder_handling
        + 0.12 * rewrite_safety
        + 0.08 * actionability
    ))

    return EvalResult(
        score_consistency=score_consistency,
        explicit_jd_keyword_accuracy=explicit_jd_keyword_accuracy,
        semantic_keyword_usefulness=semantic_keyword_usefulness,
        cv_grounding=cv_grounding,
        truthfulness=truthfulness,
        placeholder_handling=placeholder_handling,
        rewrite_safety=rewrite_safety,
        actionability=actionability,
        overall=overall,
        warnings=warnings,
        hard_hallucinations=hard_hallucinations,
        soft_inferences=soft_inferences,
        useful_adjacent_recommendations=useful_adjacent_recommendations,
        placeholder_metrics=placeholder_metrics,
        unsupported_factual_claims=unsupported_factual_claims,
        needs_user_confirmation=needs_user_confirmation,
        scored_response=scored_response,
    )
