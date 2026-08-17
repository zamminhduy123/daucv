"""Route-level tests for the decoupled LLM #1/#2/#3 pipeline API."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import UUID

from app.models.cv_document_v2 import CVDocumentV2, CVIdentity
from app.models.cv_evaluation import LLMEvaluationReport
from app.models.cv_tailoring import TailoredCVResponse, TailoringChangeItem
from app.models.domain import TailoredCV
from app.schemas.tailored_cv import TailoredCVVersionResponse
from app.services.cv_evaluator_service import EvaluationResult
from app.services.cv_tailor_service import TailoringResult


def _canonical_cv() -> dict:
    return {
        "identity": {"name": "Lan Nguyen", "headline": "ML Engineer"},
        "summary": "Built PyTorch services.",
        "education": [],
        "experience": [],
        "research_experience": [],
        "skills": {"ML": ["PyTorch"]},
        "publications": [],
        "certifications": [],
    }


def test_parse_cv_returns_llm1_canonical_json(client):
    document = CVDocumentV2(identity=CVIdentity(full_name="Lan Nguyen"))
    with patch(
        "app.api.routes.cv_pipeline.structure_cv", new_callable=AsyncMock
    ) as mock_parse:
        mock_parse.return_value = SimpleNamespace(
            document=document,
            source_text="Lan Nguyen",
            used_fallback=False,
        )
        response = client.post("/api/cv/parse", json={"cv_text": "Lan Nguyen"})

    assert response.status_code == 200
    assert response.json()["canonical_cv"]["identity"]["name"] == "Lan Nguyen"
    assert mock_parse.await_count == 1


def test_parse_cv_rejects_reprocessing_fallback(client):
    document = CVDocumentV2(
        identity=CVIdentity(full_name="Lan Nguyen"),
        requires_reprocessing=True,
    )
    with patch(
        "app.api.routes.cv_pipeline.structure_cv", new_callable=AsyncMock
    ) as mock_parse:
        mock_parse.return_value = SimpleNamespace(
            document=document,
            source_text="Lan Nguyen",
            used_fallback=True,
        )
        response = client.post("/api/cv/parse", json={"cv_text": "Lan Nguyen"})

    assert response.status_code == 503
    assert "lập bản đồ CV an toàn" in response.json()["detail"]


def test_evaluate_cv_returns_llm2_report(client):
    report = LLMEvaluationReport(overall_fit_score=82)
    with patch(
        "app.api.routes.cv_pipeline.evaluate_cv_fit", new_callable=AsyncMock
    ) as mock_evaluate:
        mock_evaluate.return_value = EvaluationResult(report=report)
        response = client.post(
            "/api/cv/evaluate",
            json={
                "canonical_cv": _canonical_cv(),
                "job_description": "PyTorch engineer",
            },
        )

    assert response.status_code == 200
    assert response.json()["evaluation"]["evaluation_mode"] == "JOB_FIT"
    assert mock_evaluate.await_count == 1


def test_tailor_cv_returns_llm3_response(client):
    canonical = _canonical_cv()
    tailored = TailoredCVResponse(
        tailored_cv=canonical,
        tailoring_summary="Keeps the candidate's existing PyTorch evidence prominent.",
    )
    with patch(
        "app.api.routes.cv_pipeline.tailor_cv", new_callable=AsyncMock
    ) as mock_tailor:
        mock_tailor.return_value = TailoringResult(response=tailored)
        response = client.post(
            "/api/cv/tailor",
            json={"canonical_cv": canonical, "job_description": "PyTorch engineer"},
        )

    assert response.status_code == 200
    assert response.json()["tailoring"]["tailoring_summary"].startswith("Keeps")
    assert mock_tailor.await_count == 1


def test_tailor_cv_accepts_no_job_description(client):
    canonical = _canonical_cv()
    tailored = TailoredCVResponse(
        tailored_cv=canonical,
        tailoring_summary="Improves the clarity of existing CV evidence.",
    )
    with patch(
        "app.api.routes.cv_pipeline.tailor_cv", new_callable=AsyncMock
    ) as mock_tailor:
        mock_tailor.return_value = TailoringResult(response=tailored)
        response = client.post("/api/cv/tailor", json={"canonical_cv": canonical})

    assert response.status_code == 200
    assert mock_tailor.await_args.args[1] is None


def test_tailor_and_save_uses_authoritative_source_and_allows_no_jd(client):
    source_document = CVDocumentV2(identity=CVIdentity(full_name="Lan Nguyen"))
    tailoring = TailoredCVResponse(
        tailored_cv=_canonical_cv(),
        change_log=[
            TailoringChangeItem(
                path="experience[0].bullets[0].text",
                original_text="Built 2 PyTorch APIs.",
                proposed_text="Built 2 PyTorch classification APIs.",
                rationale="Clarifies existing scope.",
            )
        ],
        tailoring_summary="Clarifies existing evidence.",
    )
    saved_version = TailoredCVVersionResponse(
        id=UUID("11111111-1111-4111-8111-111111111111"),
        jd_text="",
        tailored_cv=TailoredCV(),
        selected_design="classic_ats",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    with (
        patch(
            "app.api.routes.cv_pipeline.persist_pipeline_tailoring",
            new_callable=AsyncMock,
            return_value=saved_version,
        ) as mock_persist,
        patch(
            "app.api.routes.cv_pipeline.verify_pipeline_source_ticket",
            return_value="analysis-key",
        ) as verify_ticket,
    ):
        response = client.post(
            "/api/cv/tailor-and-save",
            json={
                "cv_text": "Lan Nguyen\nBuilt 2 PyTorch APIs.",
                "source_document_v2": source_document.model_dump(mode="json"),
                "source_ticket": "p1.test.ticket",
                "tailoring": tailoring.model_dump(mode="json"),
            },
        )

    assert response.status_code == 200
    verify_ticket.assert_called_once()
    assert mock_persist.await_args.kwargs["job_description"] is None
    assert mock_persist.await_args.kwargs["tailoring"] == tailoring
    assert mock_persist.await_args.kwargs["analysis_key"] == "analysis-key"
