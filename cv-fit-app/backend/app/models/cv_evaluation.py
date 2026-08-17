"""Data models for LLM #2 — CV Fit Evaluator & Judge."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class SkillRequirementMatch(BaseModel):
    """Evaluation of a specific skill or qualification requirement from the JD."""

    requirement: str = Field(
        description="The requirement or qualification specified in the Job Description"
    )
    status: Literal["matched", "partial", "missing"] = Field(
        description="Match status: matched, partial, or missing"
    )
    cv_evidence: str | None = Field(
        default=None,
        description="Direct evidence or related experience from candidate's CV",
    )
    gap_explanation: str | None = Field(
        default=None, description="Explanation if status is partial or missing"
    )


class CategoryScores(BaseModel):
    """Sub-scores across major evaluation dimensions (0-100)."""

    technical_skills: int = Field(
        default=80, ge=0, le=100, description="Technical skills alignment score (0-100)"
    )
    experience_level: int = Field(
        default=80,
        ge=0,
        le=100,
        description="Years & depth of relevant experience score (0-100)",
    )
    domain_fit: int = Field(
        default=80,
        ge=0,
        le=100,
        description="Domain knowledge & project relevance score (0-100)",
    )
    education_fit: int = Field(
        default=80,
        ge=0,
        le=100,
        description="Educational background alignment score (0-100)",
    )


class LLMEvaluationReport(BaseModel):
    """Structured evaluation report produced by LLM #2 (CV Evaluator & Judge)."""

    evaluation_mode: Literal["GENERAL_AUDIT", "JOB_FIT"] = Field(
        default="JOB_FIT",
        description="Mode: GENERAL_AUDIT (standalone CV quality check) or JOB_FIT (evaluated against a target JD)",
    )
    overall_fit_score: int = Field(
        ge=0, le=100, description="Overall fit/quality score from 0 to 100"
    )
    match_grade: (
        Literal[
            "EXCELLENT", "STRONG_FIT", "MODERATE_FIT", "WEAK_FIT", "NEEDS_IMPROVEMENT"
        ]
        | None
    ) = Field(default=None, description="Qualitative match category")
    executive_summary: str | None = Field(
        default=None,
        description="High-level 2-3 sentence summary of candidate fit or CV quality",
    )
    category_scores: CategoryScores = Field(
        default_factory=CategoryScores,
        description="Breakdown of sub-scores across key dimensions",
    )
    key_strengths: list[str] = Field(
        default_factory=list,
        description="Top 3-5 strong matching qualifications or CV strengths",
    )
    critical_gaps: list[str] = Field(
        default_factory=list,
        description="Top missing skills, experience gaps, or CV improvements needed",
    )
    skill_matrix: list[SkillRequirementMatch] = Field(
        default_factory=list,
        description="Detailed requirement-by-requirement match matrix",
    )
    actionable_recommendations: list[str] = Field(
        default_factory=list,
        description="Concrete suggestions for candidate to improve CV or fit",
    )

    @model_validator(mode="after")
    def compute_defaults(self) -> "LLMEvaluationReport":
        if not self.match_grade:
            if self.overall_fit_score >= 85:
                self.match_grade = (
                    "STRONG_FIT" if self.evaluation_mode == "JOB_FIT" else "EXCELLENT"
                )
            elif self.overall_fit_score >= 60:
                self.match_grade = (
                    "MODERATE_FIT"
                    if self.evaluation_mode == "JOB_FIT"
                    else "STRONG_FIT"
                )
            else:
                self.match_grade = (
                    "WEAK_FIT"
                    if self.evaluation_mode == "JOB_FIT"
                    else "NEEDS_IMPROVEMENT"
                )
        if not self.executive_summary:
            prefix = (
                "Job Fit Analysis"
                if self.evaluation_mode == "JOB_FIT"
                else "General CV Audit"
            )
            self.executive_summary = f"{prefix}: Candidate achieves an overall score of {self.overall_fit_score}/100 ({self.match_grade})."
        return self
