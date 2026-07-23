import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from pydantic import ValidationError

from app.models.domain import (
    EvidenceAnalysis,
    PrioritizedKeyword,
    SuggestedEdit,
    TailoredCV,
    TailoredCVSection,
)
from app.models.responses import CVAnalysisLLMResponse, CVAnalysisResponse
from app.services.cv_quality_checks import (
    EvalResult,
    build_scored_analysis,
    build_source_preserving_tailored_cv,
    classify_keyword_grounding,
    classify_rewrite_grounding,
    detect_unsupported_metrics,
    run_deterministic_eval,
)
from app.services.tailored_cv_metadata import (
    extract_target_metadata,
    issue_tailoring_entitlement,
    verify_tailoring_entitlement,
)
from app.services.tailored_cv_pdf import render_tailored_cv_html


def _analysis_response(**overrides):
    data = {
        "match_headline": "Strong fit",
        "match_summary": "Relevant profile with some gaps.",
        "technical_match": 80,
        "experience_relevance": 70,
        "keyword_coverage": 60,
        "impact_evidence": 50,
        "tone_quality": 90,
        "ats_readiness": 80,
        "missing_keywords": ["Kubernetes"],
        "suggested_edits": [
            SuggestedEdit(
                section="Experience",
                original_text="Worked on backend services.",
                improved_safe=(
                    "Optimized backend services to improve response time and "
                    "reliability for user-facing workflows."
                ),
                improved_with_placeholders=(
                    "Optimized backend services, reducing API latency from "
                    "[X ms] to [Y ms] for [workflow/users]."
                ),
                metric_questions=[
                    "What was the before/after latency?",
                    "Which workflow or user group was affected?",
                ],
                unsupported_assumptions=["Exact latency reduction"],
                rewrite_risk="needs_user_input",
                reason="Adds action and impact without inventing metrics.",
            ),
            SuggestedEdit(
                section="Skills",
                original_text="Python, APIs, databases.",
                improved_safe="Python, API development, database-backed services.",
                improved_with_placeholders=(
                    "Python, API development handling [N requests/day], "
                    "database-backed services for [workflow]."
                ),
                metric_questions=["What request volume did the APIs handle?"],
                unsupported_assumptions=[],
                rewrite_risk="safe",
                reason="Makes the skill list more specific.",
            ),
        ],
        "cv_strengths": ["Clear backend experience", "Readable structure"],
        "prioritized_keywords": [
            PrioritizedKeyword(keyword="Kubernetes", priority="High"),
        ],
        "evidence_analysis": [
            EvidenceAnalysis(
                claim="Backend optimization",
                evidence_strength="Medium",
                comment="Mentioned without metrics.",
            ),
            EvidenceAnalysis(
                claim="Kubernetes operations",
                evidence_strength="Missing",
                comment="Not found in CV.",
            ),
            EvidenceAnalysis(
                claim="API development",
                evidence_strength="Strong",
                comment="Supported by backend project details.",
            ),
        ],
    }
    data.update(overrides)
    return CVAnalysisLLMResponse(**data)


def test_build_scored_analysis_uses_weighted_subscores_and_penalties():
    response = build_scored_analysis(_analysis_response())

    assert isinstance(response, CVAnalysisResponse)
    assert response.score_breakdown is not None
    assert response.score_breakdown.raw_score == 72
    # Aggressive penalties: High=8, unsupported_claim=2, total=10
    assert response.score_breakdown.weighted_missing_requirement_score == 8
    assert response.score_breakdown.critical_missing_penalty == 0
    assert response.score_breakdown.high_missing_penalty == 8
    assert response.score_breakdown.missing_requirement_penalty == 8
    assert response.score_breakdown.unsupported_claim_penalty == 2
    assert response.score_breakdown.total_penalty == 10
    # role_fit_score = raw_score (no penalty)
    assert response.role_fit_score == 72
    # CV Match = raw_score - aggressive_penalty
    assert response.match_score == 62
    assert response.score_breakdown.final_score == 62
    assert response.match_headline == "Có tiềm năng, nhưng CV cần tối ưu thêm theo JD."


def test_source_preserving_tailored_cv_keeps_all_recognized_sections_and_bullets():
    source = """Nguyen Thanh Minh Duy
duy@example.com | LinkedIn
Professional Summary
Builds production ML systems.
Technical Skills
• PyTorch
• FastAPI
Work Experience
Zalo — Software Engineer
• Shipped features
• Reduced latency by 30%
Projects
Be Dau
• Built career platform
Publications
• Research paper
Education & Certifications
MSc Computer Science"""
    cv = build_source_preserving_tailored_cv(_analysis_response(), source)
    rendered = " ".join(item for section in cv.sections for item in section.items)
    assert cv.name == "Nguyen Thanh Minh Duy"
    assert cv.contact_lines == ["duy@example.com | LinkedIn"]
    assert "Builds production ML systems." in cv.summary
    assert "Reduced latency by 30%" in rendered
    assert "Built career platform" in rendered
    assert "Research paper" in rendered
    assert "MSc Computer Science" in rendered


def test_source_preserving_tailored_cv_joins_pdf_wrapped_bullet_lines():
    source = """Duy
duy@example.com
Work Experience
Company A
Engineer Jan 2024 - Present
• Built an ML platform for production users
across multiple regions.
• Reduced processing latency by 30%
while maintaining reliability."""
    cv = build_source_preserving_tailored_cv(_analysis_response(), source)
    items = cv.sections[0].items
    assert items == [
        "Company A",
        "Engineer Jan 2024 - Present",
        "• Built an ML platform for production users across multiple regions.",
        "• Reduced processing latency by 30% while maintaining reliability.",
    ]


def test_source_preserving_tailored_cv_does_not_treat_managerial_bullet_wrap_as_role():
    source = """Duy
duy@example.com
Projects
AI Interview Simulation
• Engineered dynamic interview personas, enabling realistic and adaptable
simulations for diverse HR, technical, and managerial interview scenarios.
Interactive Video Retrieval System
• Built a multimodal retrieval system."""

    cv = build_source_preserving_tailored_cv(_analysis_response(), source)

    assert cv.sections[0].items == [
        "AI Interview Simulation",
        "• Engineered dynamic interview personas, enabling realistic and adaptable simulations for diverse HR, technical, and managerial interview scenarios.",
        "Interactive Video Retrieval System",
        "• Built a multimodal retrieval system.",
    ]


def test_source_preserving_tailored_cv_keeps_next_job_separate_from_previous_bullet():
    source = """Duy
duy@example.com
Work Experience
Company A
Engineer Jan 2024 - Present
• Built a production ML platform.
Company B
Software Engineer May 2022 - Dec 2023
• Shipped customer-facing features."""

    cv = build_source_preserving_tailored_cv(_analysis_response(), source)

    assert cv.sections[0].items == [
        "Company A",
        "Engineer Jan 2024 - Present",
        "• Built a production ML platform.",
        "Company B",
        "Software Engineer May 2022 - Dec 2023",
        "• Shipped customer-facing features.",
    ]


def test_source_preserving_tailored_cv_keeps_multiline_identity_and_vietnamese_sections():
    source = """Nguyễn Thanh Minh Duy
Machine Learning Engineer
duy@example.com
+84 901 234 567
linkedin.com/in/duy
TÓM TẮT
Xây dựng hệ thống machine learning thực tế.
KINH NGHIỆM LÀM VIỆC
Zalo
Kỹ sư phần mềm
• Phát triển tính năng cho người dùng.
KỸ NĂNG
Python, PyTorch, FastAPI"""

    cv = build_source_preserving_tailored_cv(_analysis_response(), source)

    assert cv.name == "Nguyễn Thanh Minh Duy"
    assert cv.contact_lines == [
        "duy@example.com",
        "+84 901 234 567",
        "linkedin.com/in/duy",
    ]
    assert cv.summary == "Xây dựng hệ thống machine learning thực tế."
    assert [section.title for section in cv.sections] == [
        "KINH NGHIỆM LÀM VIỆC",
        "KỸ NĂNG",
    ]


def test_source_preserving_tailored_cv_rejects_unsupported_llm_rewrite_and_identity():
    source = """Duy Nguyen
duy@example.com
Summary
Backend engineer building APIs.
Experience
Acme — Engineer
• Worked on backend services.
Skills
Python, APIs, databases."""
    response = _analysis_response(
        tailored_cv={
            "name": "Wrong Generated Name",
            "headline": "Backend Engineer",
            "contact_lines": ["wrong@example.com"],
            "summary": "Backend engineer focused on reliable API platforms.",
            "sections": [
                {
                    "title": "Experience",
                    "items": [
                        "Acme — Engineer",
                        "• Built and maintained reliable backend services.",
                    ],
                },
                {
                    "title": "Skills",
                    "items": ["Python, API development, database-backed services."],
                },
            ],
        },
    )

    cv = build_source_preserving_tailored_cv(response, source)

    assert cv.name == "Duy Nguyen"
    assert cv.contact_lines == ["duy@example.com"]
    assert cv.summary == "Backend engineer building APIs."
    assert cv.sections[0].items[1] == "• Worked on backend services."
    assert cv.sections[1].items == ["Python, APIs, databases."]


def test_source_preserving_tailored_cv_applies_safe_edit_across_pdf_line_wraps():
    source = """Duy
duy@example.com
Experience
• Built backend services for customer-facing
workflows and internal operations."""
    safe_edit = SuggestedEdit(
        section="Experience",
        original_text="Built backend services for customer-facing workflows and internal operations.",
        improved_safe="Built customer-facing backend services for internal workflows and operations.",
        improved_with_placeholders="",
        metric_questions=[],
        unsupported_assumptions=[],
        rewrite_risk="safe",
        reason="Reorders source-supported wording.",
    )
    response = _analysis_response(suggested_edits=[safe_edit, safe_edit])

    cv = build_source_preserving_tailored_cv(response, source)

    assert cv.sections[0].items == [
        "• Built customer-facing backend services for internal workflows and operations.",
    ]


def test_source_preserving_tailored_cv_rejects_self_labeled_safe_new_claims():
    source = """Duy
duy@example.com
Experience
• Worked on backend services."""
    unsafe_edit = SuggestedEdit(
        section="Experience",
        original_text="Worked on backend services.",
        improved_safe="Led highly reliable backend services at global scale.",
        improved_with_placeholders="",
        metric_questions=[],
        unsupported_assumptions=[],
        rewrite_risk="safe",
        reason="Model incorrectly marked an unsupported claim safe.",
    )
    response = _analysis_response(suggested_edits=[unsafe_edit, unsafe_edit])

    cv = build_source_preserving_tailored_cv(response, source)

    assert cv.sections[0].items == ["• Worked on backend services."]


def test_source_preserving_tailored_cv_job_metadata_boundaries():
    source = """Duy Nguyen
duy@example.com
Kinh nghiệm làm việc
Công ty VNG
Kỹ sư phần mềm Tháng 1/2023 - Hiện tại
• Phát triển hệ thống tin nhắn quy mô lớn
Công ty Viettel
Lập trình viên Java Tháng 5/2021 - Tháng 12/2022
• Xây dựng API và cơ sở dữ liệu"""

    cv = build_source_preserving_tailored_cv(_analysis_response(), source)

    assert cv.sections[0].items == [
        "Công ty VNG",
        "Kỹ sư phần mềm Tháng 1/2023 - Hiện tại",
        "• Phát triển hệ thống tin nhắn quy mô lớn",
        "Công ty Viettel",
        "Lập trình viên Java Tháng 5/2021 - Tháng 12/2022",
        "• Xây dựng API và cơ sở dữ liệu",
    ]


def test_source_preserving_tailored_cv_multilingual_headings_accents():
    source = """Nguyễn Văn A
nguyenvana@example.com
GIỚI THIỆU
Kỹ sư phần mềm giàu kinh nghiệm.
KINH NGHIỆM LÀM VIỆC
• Lập trình ReactJS.
HỌC VẤN
Đại học Bách Khoa
CHỨNG CHỈ
IELTS 7.5"""

    cv = build_source_preserving_tailored_cv(_analysis_response(), source)

    assert cv.name == "Nguyễn Văn A"
    assert cv.summary == "Kỹ sư phần mềm giàu kinh nghiệm."
    assert len(cv.sections) == 3
    assert cv.sections[0].title == "KINH NGHIỆM LÀM VIỆC"
    assert cv.sections[1].title == "HỌC VẤN"
    assert cv.sections[2].title == "CHỨNG CHỈ"


def test_source_preserving_tailored_cv_multiline_identity_vietnamese():
    source = """Trần Thị B
Lập trình viên Frontend
SĐT: +84987654321
Email: tranthib@example.com
Địa chỉ: Quận 7, TP. Hồ Chí Minh, Việt Nam
LinkedIn: linkedin.com/in/tranthib
TÓM TẮT
Kinh nghiệm lập trình ứng dụng web."""

    cv = build_source_preserving_tailored_cv(_analysis_response(), source)

    assert cv.name == "Trần Thị B"
    assert "SĐT: +84987654321" in cv.contact_lines
    assert "Email: tranthib@example.com" in cv.contact_lines
    assert "Địa chỉ: Quận 7, TP. Hồ Chí Minh, Việt Nam" in cv.contact_lines
    assert "LinkedIn: linkedin.com/in/tranthib" in cv.contact_lines
    assert cv.summary == "Kinh nghiệm lập trình ứng dụng web."


def test_tailored_cv_metadata_uses_explicit_role_and_company_labels():
    role, company = extract_target_metadata(
        """Vị trí: Machine Learning Engineer
Công ty: Acme AI
Mô tả công việc:
Xây dựng hệ thống ML.""",
    )

    assert role == "Machine Learning Engineer"
    assert company == "Acme AI"


def test_tailoring_entitlement_is_bound_to_user_cv_and_jd(monkeypatch):
    from uuid import UUID

    monkeypatch.setenv("NEXTAUTH_SECRET", "test-secret")
    user_id = UUID("00000000-0000-0000-0000-000000000001")
    token = issue_tailoring_entitlement(user_id, "source cv", "target jd")
    second_token = issue_tailoring_entitlement(user_id, "source cv", "target jd")

    assert verify_tailoring_entitlement(token, user_id, "source cv", "target jd")
    assert token != second_token
    with pytest.raises(ValueError):
        verify_tailoring_entitlement(token, user_id, "changed cv", "target jd")


@pytest.mark.parametrize(
    "design",
    ["classic_ats", "modern_professional", "compact_one_page"],
)
def test_pdf_html_contains_complete_escaped_cv_for_every_design(design):
    cv = type(_analysis_response().tailored_cv).model_validate(
        {
            "name": "Duy <Nguyen>",
            "headline": "Engineer",
            "contact_lines": ["duy@example.com"],
            "summary": "Backend engineer.",
            "sections": [
                {"title": "Experience", "items": ["• Built APIs & services."]},
                {"title": "Skills", "items": ["Python"]},
            ],
        },
    )

    html = render_tailored_cv_html(cv, design)

    assert f'class="{design}"' in html
    assert "Duy &lt;Nguyen&gt;" in html
    assert "Built APIs &amp; services." in html
    assert "Experience" in html
    assert "Skills" in html


def test_pdf_html_bolds_each_experience_entry_headline():
    cv = type(_analysis_response().tailored_cv).model_validate(
        {
            "name": "Duy",
            "sections": [
                {
                    "title": "Experience",
                    "items": [
                        "Company A",
                        "Engineer",
                        "• Built APIs.",
                        "Company B",
                        "Software Engineer",
                        "• Shipped features.",
                    ],
                },
            ],
        },
    )

    html = render_tailored_cv_html(cv, "classic_ats")

    assert '<p class="headline">Company A</p>' in html
    assert '<p class="headline">Company B</p>' in html
    assert '<p class="item">Software Engineer</p>' in html


def test_pdf_html_repairs_wrapped_bullet_before_highlighting_next_entry():
    cv = TailoredCV(
        name="Duy Nguyen",
        headline="Engineer",
        contact_lines=[],
        summary="",
        sections=[
            TailoredCVSection(
                title="Projects",
                items=[
                    "AI Interview Simulation",
                    "• Engineered dynamic personas, enabling realistic and adaptable",
                    "simulations for diverse HR, technical, and managerial interviews.",
                    "Interactive Video Retrieval System",
                    "• Built a multimodal retrieval system.",
                ],
            ),
        ],
    )

    html = render_tailored_cv_html(cv, "classic_ats")

    assert "adaptable simulations for diverse HR" in html
    assert '<p class="headline">Interactive Video Retrieval System</p>' in html
    assert '<p class="headline">simulations for diverse HR' not in html


@pytest.mark.parametrize("title", ["Technical Skills", "KỸ NĂNG", "Ky nang"])
def test_modern_pdf_places_skill_aliases_in_sidebar(title):
    cv = type(_analysis_response().tailored_cv).model_validate(
        {
            "name": "Duy",
            "sections": [{"title": title, "items": ["Python"]}],
        },
    )

    html = render_tailored_cv_html(cv, "modern_professional")
    sidebar = html.split("</aside>", 1)[0]

    assert title in sidebar


def test_llm_schema_does_not_include_or_accept_match_score():
    schema = CVAnalysisLLMResponse.model_json_schema()

    assert "match_score" not in schema["properties"]

    payload = _analysis_response().model_dump()
    payload["match_score"] = 99

    with pytest.raises(ValidationError):
        CVAnalysisLLMResponse(**payload)


def test_api_schema_includes_backend_score_fields():
    schema = CVAnalysisResponse.model_json_schema()

    assert "role_fit_score" in schema["properties"]
    assert "match_score" in schema["properties"]
    assert "score_breakdown" in schema["properties"]
    assert "role_fit_score" in schema["required"]
    assert "match_score" in schema["required"]
    assert "score_breakdown" in schema["required"]


def test_llm_schema_trims_oversized_keyword_lists():
    payload = _analysis_response().model_dump()
    payload["missing_keywords"] = [f"keyword-{index}" for index in range(12)]
    payload["prioritized_keywords"] = [
        {"keyword": f"keyword-{index}", "priority": "Low"} for index in range(9)
    ]

    response = CVAnalysisLLMResponse(**payload)

    assert len(response.missing_keywords) == 6
    assert response.missing_keywords == [f"keyword-{index}" for index in range(6)]
    assert len(response.prioritized_keywords) == 6
    assert [item.keyword for item in response.prioritized_keywords] == [
        f"keyword-{index}" for index in range(6)
    ]


def test_llm_schema_accepts_short_evidence_analysis():
    payload = _analysis_response().model_dump()
    payload["evidence_analysis"] = [
        {
            "claim": "Relevant backend work",
            "evidence_strength": "Medium",
            "comment": "Some backend evidence is visible.",
        },
        {
            "claim": "Role alignment",
            "evidence_strength": "Weak",
            "comment": "Needs stronger JD-specific evidence.",
        },
    ]

    response = CVAnalysisLLMResponse(**payload)

    assert len(response.evidence_analysis) == 2


def test_llm_schema_pads_missing_minimum_lists_with_safe_fallbacks():
    payload = _analysis_response().model_dump()
    payload["suggested_edits"] = []
    payload["cv_strengths"] = []
    payload["evidence_analysis"] = []

    response = CVAnalysisLLMResponse(**payload)

    assert len(response.suggested_edits) == 2
    assert len(response.cv_strengths) == 2
    assert len(response.evidence_analysis) == 1
    assert response.suggested_edits[0].rewrite_risk == "needs_user_input"


def test_metric_placeholders_do_not_count_as_fabricated_safe_metrics():
    response = _analysis_response()

    assert detect_unsupported_metrics(response, "Worked on backend services.") == []
    assert (
        response.suggested_edits[0].upgraded_text
        == response.suggested_edits[0].improved_safe
    )


def test_keyword_grounding_allows_soft_inference_and_adjacent_recommendations():
    response = _analysis_response(
        missing_keywords=["Backend scalability", "RAG evaluation", "Quantum ledger"],
        prioritized_keywords=[
            PrioritizedKeyword(keyword="Backend scalability", priority="High"),
            PrioritizedKeyword(keyword="RAG evaluation", priority="Low"),
            PrioritizedKeyword(keyword="Quantum ledger", priority="Critical"),
        ],
    )

    result = classify_keyword_grounding(
        response,
        jd_text="Build backend APIs and scalable system architecture for LLM application quality.",
    )

    assert any("Backend scalability" in item for item in result["soft_inferences"])
    assert any(
        "RAG evaluation" in item for item in result["useful_adjacent_recommendations"]
    )
    assert any("Quantum ledger" in item for item in result["hard_hallucinations"])


def test_rewrite_grounding_separates_placeholders_from_unsupported_facts():
    response = _analysis_response(
        suggested_edits=[
            SuggestedEdit(
                section="Experience",
                original_text="Optimized backend services.",
                improved_safe="Optimized backend services, reducing latency by 35%.",
                improved_with_placeholders="Optimized backend services, reducing latency by [X%].",
                metric_questions=["What was the measured latency reduction?"],
                unsupported_assumptions=["Exact latency reduction"],
                rewrite_risk="needs_user_input",
                reason="Needs a real metric before using the quantified version.",
            ),
            SuggestedEdit(
                section="Skills",
                original_text="Python, APIs, databases.",
                improved_safe="Python, API development, database-backed services.",
                improved_with_placeholders="Python, API development for [workflow].",
                metric_questions=["Which workflow did this support?"],
                unsupported_assumptions=[],
                rewrite_risk="safe",
                reason="Makes the skill list more specific.",
            ),
        ],
    )

    result = classify_rewrite_grounding(response, cv_text="Optimized backend services.")

    assert any("35" in item for item in result["unsupported_factual_claims"])
    assert any("[X%]" in item for item in result["placeholder_metrics"])
    assert any(
        "Exact latency reduction" in item for item in result["needs_user_confirmation"]
    )


def test_run_deterministic_eval_returns_scored_response():
    result = run_deterministic_eval(
        _analysis_response(),
        cv_text="Worked on backend services.",
        jd_text="We need Kubernetes and API development.",
    )

    assert isinstance(result, EvalResult)
    assert result.schema_valid is True
    assert isinstance(result.warnings, list)
    assert isinstance(result.scored_response, CVAnalysisResponse)
    assert result.scored_response.role_fit_score == 72
    assert result.scored_response.match_score == 62
    assert result.placeholder_metrics
