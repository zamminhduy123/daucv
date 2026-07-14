"""Endpoint tests that verify route registration and input validation.

No LLM calls — these only test that routes exist, accept valid input,
and reject invalid input with 422 (Pydantic validation errors).
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

# All POST endpoints that should be registered.
# If a new route is added, append to this list.
POST_ROUTES = [
    "/api/upload-and-match",
    "/api/extract-pdf",
    "/api/analyze-cv",
    "/api/writer/generate",
    "/api/interview/chat",
    "/api/interview/finish",
    "/api/interview/tts",
    "/api/jobs/parse-profile",
    "/api/jobs/search",
    "/api/user/feedback",
]


@pytest.mark.parametrize(
    "path", POST_ROUTES, ids=lambda p: p.replace("/", "_").strip("_")
)
def test_post_route_is_registered(client: TestClient, path: str) -> None:
    """Each POST route should exist (not 404). Hit with GET; we only care about route presence."""
    resp = client.get(path)
    # 405 = route exists but wrong method; 200 = works with GET; anything else ≠ 404
    assert resp.status_code != 404, f"Route {path} is not registered (404)"


def test_analyze_cv_rejects_empty_body(client: TestClient) -> None:
    resp = client.post("/api/analyze-cv", json={})
    assert resp.status_code == 422


def test_tailored_cv_create_requires_analysis_entitlement(client: TestClient) -> None:
    resp = client.post(
        "/api/user/tailored-cvs",
        json={
            "tailored_cv": {"name": "Duy", "sections": []},
            "source_cv_text": "Duy\nduy@example.com",
            "jd_text": "Backend Engineer",
        },
    )
    assert resp.status_code == 422


def test_tailored_cv_routes_validate_version_id(client: TestClient) -> None:
    patch_response = client.patch(
        "/api/user/tailored-cvs/not-a-uuid",
        json={"selected_design": "modern_professional"},
    )
    pdf_response = client.get("/api/user/tailored-cvs/not-a-uuid/pdf")

    assert patch_response.status_code == 400
    assert pdf_response.status_code == 400


def test_tailored_cv_list_returns_controlled_future_schema_error(
    client: TestClient,
) -> None:
    from app.services.tailored_cv_service import UnsupportedCVSchemaVersionError

    with patch(
        "app.services.tailored_cv_service.list_versions",
        new=AsyncMock(side_effect=UnsupportedCVSchemaVersionError(3)),
    ):
        response = client.get("/api/user/tailored-cvs")

    assert response.status_code == 409
    assert "schema 3" in response.json()["detail"]


def test_analyze_cv_rejects_no_cv_text(client: TestClient) -> None:
    resp = client.post("/api/analyze-cv", json={"cv_text": ""})
    assert resp.status_code == 422


def test_analyze_cv_422_with_whitespace_only(client: TestClient) -> None:
    resp = client.post("/api/analyze-cv", json={"cv_text": "   "})
    assert resp.status_code == 422


def test_writer_rejects_empty_cv(client: TestClient) -> None:
    resp = client.post(
        "/api/writer/generate",
        json={"cv_text": "", "writing_type": "email", "tone": "Chuyên nghiệp"},
    )
    assert resp.status_code == 422


def test_interview_chat_accepts_empty_history_first_turn(client: TestClient) -> None:
    """Empty chat history on first turn is valid — the route has special first-turn logic."""
    resp = client.post(
        "/api/interview/chat",
        json={
            "cv_text": "Test CV",
            "chat_history": [],
            "current_question": 1,
            "total_questions": 5,
        },
    )
    # Should NOT be 422 — the route handles first turn specially
    assert resp.status_code != 422


def test_interview_finish_rejects_empty_history(client: TestClient) -> None:
    resp = client.post(
        "/api/interview/finish",
        json={
            "cv_text": "Test CV",
            "chat_history": [],
            "interview_type": "general",
        },
    )
    assert resp.status_code == 422


def test_parse_profile_rejects_empty_cv(client: TestClient) -> None:
    resp = client.post("/api/jobs/parse-profile", json={"cv_text": ""})
    assert resp.status_code == 422


def test_tts_rejects_empty_text(client: TestClient) -> None:
    resp = client.post("/api/interview/tts", json={"text": ""})
    assert resp.status_code == 400


def test_tts_rejects_no_body(client: TestClient) -> None:
    resp = client.post("/api/interview/tts", json={})
    assert resp.status_code == 422


def test_jobs_search_accepts_minimal_body(client: TestClient) -> None:
    """Job search failures must degrade to a response instead of an unhandled 500."""
    resp = client.post("/api/jobs/search", json={"cv_text": "Test CV"})
    assert resp.status_code == 200, resp.text


def test_get_user_profile(client: TestClient) -> None:
    resp = client.get("/api/user/profile")
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "test@example.com"
    assert data["credits"] == 10
    assert data["active_cv"]["cv_filename"] == "test.pdf"
    assert "total_cvs" in data
    assert "active_cv_age_days" in data


def test_list_user_cvs(client: TestClient) -> None:
    resp = client.get("/api/user/cvs")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["cvs"], list)
    assert len(data["cvs"]) == 1
    assert data["cvs"][0]["cv_filename"] == "test.pdf"


def test_upload_user_cv(client: TestClient) -> None:
    resp = client.post(
        "/api/user/cv",
        json={"cv_text": "Updated CV Text", "cv_filename": "updated_resume.pdf"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["cv_filename"] == "test.pdf"  # Returned by mock fetchrow
    assert data["cv_text"] == "Sample CV Text"


def test_update_active_cv(client: TestClient) -> None:
    resp = client.put(
        "/api/user/cv/active",
        json={"cv_text": "Draft CV Text", "cv_filename": "draft_resume.pdf"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["cv_filename"] == "test.pdf"  # Returned by mock fetchrow
    assert data["cv_text"] == "Sample CV Text"


def test_deactivate_user_cv(client: TestClient) -> None:
    cv_id = "12345678-1234-1234-1234-123456789012"
    resp = client.delete(f"/api/user/cv/{cv_id}")
    assert resp.status_code == 200
    assert resp.json() == {"success": True}


@patch(
    "app.api.routes.user.user_cv_service.submit_user_feedback", new_callable=AsyncMock
)
def test_submit_feedback_route(mock_submit: AsyncMock, client: TestClient) -> None:
    mock_submit.return_value = (5, 15)  # 5 credits rewarded, new balance 15
    resp = client.post(
        "/api/user/feedback",
        json={"rating": 5, "content": "This application is amazing!"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["credits_rewarded"] == 5
    assert data["new_credits"] == 15
    assert "Đóng góp thành công" in data["message"]


def test_list_feedbacks_route(client: TestClient) -> None:
    resp = client.get("/api/feedbacks")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@patch(
    "app.api.routes.tailored_cv.tailored_cv_service.get_version", new_callable=AsyncMock
)
def test_get_tailored_cv_pdf_ownership(mock_get: AsyncMock, client: TestClient) -> None:
    from app.services.tailored_cv_service import TailoredCVNotFoundError

    mock_get.side_effect = TailoredCVNotFoundError()

    resp = client.get("/api/user/tailored-cvs/12345678-1234-1234-1234-123456789012/pdf")
    assert resp.status_code == 404


@patch("app.api.routes.tailored_cv.generate_tailored_cv_pdf", new_callable=AsyncMock)
@patch(
    "app.api.routes.tailored_cv.tailored_cv_service.get_version", new_callable=AsyncMock
)
def test_get_tailored_cv_pdf_downloads_pdf(
    mock_get: AsyncMock, mock_generate: AsyncMock, client: TestClient
) -> None:
    from types import SimpleNamespace
    from uuid import UUID

    from app.models.domain import TailoredCV

    version_id = UUID("12345678-1234-1234-1234-123456789012")
    mock_get.return_value = SimpleNamespace(
        id=version_id,
        tailored_cv=TailoredCV(name="Duy", sections=[]),
        selected_design="classic_ats",
        document_v2=None,
        source_language="vi",
    )
    mock_generate.return_value = b"%PDF-test"

    resp = client.get(f"/api/user/tailored-cvs/{version_id}/pdf")

    assert resp.status_code == 200
    assert resp.content.startswith(b"%PDF")
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment" in resp.headers["content-disposition"]


@patch(
    "app.api.routes.tailored_cv.tailored_cv_service.update_design",
    new_callable=AsyncMock,
)
def test_update_tailored_cv_design_ownership(
    mock_update: AsyncMock, client: TestClient
) -> None:
    from app.services.tailored_cv_service import TailoredCVNotFoundError

    mock_update.side_effect = TailoredCVNotFoundError()

    resp = client.patch(
        "/api/user/tailored-cvs/12345678-1234-1234-1234-123456789012",
        json={"selected_design": "modern_professional"},
    )
    assert resp.status_code == 404


@patch(
    "app.api.routes.tailored_cv.tailored_cv_service.delete_version",
    new_callable=AsyncMock,
)
def test_delete_tailored_cv_version_ownership(
    mock_delete: AsyncMock, client: TestClient
) -> None:
    from app.services.tailored_cv_service import TailoredCVNotFoundError

    mock_delete.side_effect = TailoredCVNotFoundError()

    resp = client.delete("/api/user/tailored-cvs/12345678-1234-1234-1234-123456789012")
    assert resp.status_code == 404
