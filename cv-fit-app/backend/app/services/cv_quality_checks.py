"""
CV Analysis — Deterministic Quality Checks
============================================
Post-hoc evaluation harness that runs entirely on the LLM's structured output
(no additional API calls). Catches score inconsistencies, hallucinated keywords,
and fabricated impact metrics before the response reaches the frontend.
"""

import re

from pydantic import BaseModel, Field

from app.models.responses import (
    CVAnalysisLLMResponse,
    CVAnalysisResponse,
    ScoreBreakdown,
)

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
    "and",
    "or",
    "the",
    "for",
    "with",
    "from",
    "into",
    "that",
    "this",
    "you",
    "your",
    "are",
    "can",
    "will",
    "must",
    "need",
    "needs",
    "using",
    "use",
    "job",
    "role",
    "skill",
    "skills",
    "experience",
    "knowledge",
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
    warnings: list[str]
    hard_hallucinations: list[str]
    soft_inferences: list[str]
    useful_adjacent_recommendations: list[str]
    placeholder_metrics: list[str]
    unsupported_factual_claims: list[str]
    needs_user_confirmation: list[str]
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


def check_score_consistency(response: CVAnalysisResponse) -> list[str]:
    """
    Detect contradictions between ``match_score`` and the six sub-scores or
    the ``prioritized_keywords`` urgency level.
    """
    warnings: list[str] = []

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
    Calculate scores from sub-scores and deterministic penalties.

    Two scores are produced:
      - role_fit_score  ("Role Fit")  = raw LLM sub-score average — what a human gives
      - match_score     ("CV Match")  = role_fit_score minus penalties for missing JD keywords
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
    weighted_missing_requirement_score = round(
        sum(PRIORITY_WEIGHTS[item.priority] for item in response.prioritized_keywords)
    )
    unsupported_claim_count = sum(
        1
        for edit in response.suggested_edits
        if edit.rewrite_risk == "risky" or edit.unsupported_assumptions
    )

    # Aggressive penalties for "CV Match" — HR/ATS screening reality
    critical_missing_penalty = 12 * critical_missing_count
    high_missing_penalty = 8 * high_missing_count
    missing_requirement_penalty = round(weighted_missing_requirement_score)
    unsupported_claim_penalty = 2 * unsupported_claim_count
    total_penalty = missing_requirement_penalty + unsupported_claim_penalty
    # CV Match score — raw score minus penalties (can be low when JD keywords missing)
    match_score = max(0, min(100, round(raw_score - total_penalty)))

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
        final_score=match_score,
    )
    match_headline, match_summary = _build_deterministic_match_copy(
        response=response,
        role_fit_score=raw_score,
        match_score=match_score,
        total_penalty=total_penalty,
    )
    response_data = response.model_dump()
    response_data.update(
        match_headline=match_headline,
        match_summary=match_summary,
        role_fit_score=raw_score,
        match_score=match_score,
        score_breakdown=score_breakdown,
    )
    return CVAnalysisResponse(**response_data)


def _build_deterministic_match_copy(
    *,
    response: CVAnalysisLLMResponse,
    role_fit_score: int,
    match_score: int,
    total_penalty: int,
) -> tuple[str, str]:
    """Build headline + summary explaining Role Fit and CV Match scores."""
    penalty_reason = _summarize_penalty_reason(response)

    # Headlines based on CV Match (the penalized score — what HR/ATS screens see)
    if match_score >= 85:
        headline = "Rất phù hợp — CV đã bám sát JD và có tín hiệu ứng tuyển mạnh."
    elif match_score >= 70:
        headline = "Phù hợp tốt — CV có nền tảng mạnh nhưng vẫn còn điểm cần tối ưu."
    elif match_score >= 55:
        headline = "Có tiềm năng, nhưng CV cần tối ưu thêm theo JD."
    elif match_score >= 40:
        headline = "Chưa đủ khớp — CV cần cải thiện rõ trước khi ứng tuyển."
    else:
        headline = "Không phù hợp — CV thiếu nhiều yêu cầu quan trọng của JD."

    # Summary: explain the gap between Role Fit and CV Match
    if role_fit_score - match_score >= 10:
        summary = (
            f"Role Fit hiện là {role_fit_score}%, cho thấy nền tảng ứng viên khá tốt. "
            f"Nhưng CV Match chỉ {match_score}% vì bị trừ {total_penalty} điểm "
            f"do {penalty_reason}. "
            f"{response.match_summary}"
        )
    elif total_penalty > 0 and total_penalty >= 3:
        summary = (
            f"CV Match: {match_score}%. "
            f"Bị trừ {total_penalty} điểm do {penalty_reason}. "
            f"{response.match_summary}"
        )
    else:
        summary = response.match_summary

    return headline, summary


def _summarize_penalty_reason(response: CVAnalysisLLMResponse) -> str:
    critical_count = sum(
        1 for item in response.prioritized_keywords if item.priority == "Critical"
    )
    high_count = sum(
        1 for item in response.prioritized_keywords if item.priority == "High"
    )
    unsupported_count = sum(
        1
        for edit in response.suggested_edits
        if edit.rewrite_risk == "risky" or edit.unsupported_assumptions
    )

    reasons: list[str] = []
    if critical_count:
        reasons.append(f"{critical_count} yêu cầu Critical còn thiếu")
    if high_count:
        reasons.append(f"{high_count} yêu cầu High-priority còn thiếu")
    if unsupported_count:
        reasons.append(f"{unsupported_count} đề xuất cần người dùng xác nhận thêm")

    return ", ".join(reasons) if reasons else "các tín hiệu CV chưa đủ rõ so với JD"


# ---------------------------------------------------------------------------
# 2. Missing-keyword grounding
# ---------------------------------------------------------------------------


def classify_keyword_grounding(
    response: CVAnalysisLLMResponse,
    jd_text: str,
) -> dict[str, list[str]]:
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
        _normalize(item.keyword): item.priority
        for item in response.prioritized_keywords
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
) -> dict[str, list[str]]:
    """
    Extract numbers / percentages / multipliers from each
    ``suggested_edits[].improved_safe`` and classify unsupported claims.
    Placeholder metrics in ``improved_with_placeholders`` are expected and safe
    when they remain bracketed.
    """
    unsupported_factual_claims: list[str] = []
    placeholder_metrics: list[str] = []
    needs_user_confirmation: list[str] = []
    cv_metrics = _extract_metrics(cv_text)

    for edit in response.suggested_edits:
        safe_metrics = _extract_metrics(edit.improved_safe)
        original_metrics = _extract_metrics(edit.original_text)

        # Metrics already present in the original bullet are fine
        novel_metrics = safe_metrics - original_metrics - cv_metrics

        for metric in sorted(novel_metrics):
            unsupported_factual_claims.append(
                f'{edit.section}: metric "{metric}" appears in improved_safe but is not found in the original CV.'
            )

        placeholders = re.findall(r"\[[^\]]+\]", edit.improved_with_placeholders)
        for placeholder in placeholders:
            if _extract_metrics(placeholder) or any(
                token in placeholder.lower()
                for token in (
                    "%",
                    "before",
                    "after",
                    "user",
                    "workflow",
                    "request",
                    "latency",
                )
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
) -> list[str]:
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
        100
        - 25 * len(unsupported_factual_claims)
        - 10
        * sum(1 for edit in response.suggested_edits if edit.rewrite_risk == "risky")
    )
    score_consistency = _clamp_score(100 - 20 * len(score_warnings))
    cv_grounding = _clamp_score(
        100 - 25 * len(unsupported_factual_claims) - 15 * len(hard_hallucinations)
    )
    actionability = _clamp_score(
        70 + 5 * len(response.suggested_edits) + 3 * len(needs_user_confirmation)
    )
    overall = _clamp_score(
        round(
            0.15 * score_consistency
            + 0.12 * explicit_jd_keyword_accuracy
            + 0.10 * semantic_keyword_usefulness
            + 0.15 * cv_grounding
            + 0.18 * truthfulness
            + 0.10 * placeholder_handling
            + 0.12 * rewrite_safety
            + 0.08 * actionability
        )
    )

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
