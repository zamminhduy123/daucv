"""Unit tests for the bounded-operation LLM #3 tailoring contract."""

from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from app.models.cv_tailoring import LLMTailoredCVResponse, LLMTailoringOperation
from app.prompts.system_prompts import build_cv_tailor_prompt
from app.services.cv_tailor_service import tailor_cv


def _sample_cv() -> dict:
    return {
        "identity": {"name": "Lan Nguyen", "headline": "ML Engineer"},
        "summary": "Built PyTorch services for classification.",
        "education": [],
        "experience": [
            {
                "title": "ML Engineer",
                "organization": "Example Labs",
                "date": "2024 - Present",
                "bullets": [{"text": "Built 2 PyTorch APIs.", "source": ["b1"]}],
                "source": ["b1"],
            }
        ],
        "research_experience": [],
        "skills": {"ML": ["PyTorch", "FastAPI"]},
        "publications": [],
        "certifications": [],
    }


def _sample_response() -> LLMTailoredCVResponse:
    return LLMTailoredCVResponse(
        change_log=[
            LLMTailoringOperation(
                path="experience[0].bullets[0].text",
                proposed_text="Built 2 PyTorch classification APIs.",
                rationale="Makes the existing classification context more visible.",
            )
        ],
        tailoring_summary="Highlights existing PyTorch API work for the target role.",
    )


def test_llm3_contract_is_bounded_operations_not_a_full_cv():
    response = _sample_response()
    assert "tailored_cv" not in response.model_dump()
    assert response.change_log[0].path == "experience[0].bullets[0].text"

    with pytest.raises(ValidationError, match="Extra inputs"):
        LLMTailoredCVResponse.model_validate(
            {
                "tailored_cv": _sample_cv(),
                "change_log": [],
                "tailoring_summary": "Invalid legacy full-CV response.",
            }
        )


def test_llm3_contract_rejects_captured_gemini_change_shape():
    """Regression for the real `{\"change\": ...}` response logged on 2026-08-11."""
    with pytest.raises(ValidationError, match="Field required"):
        LLMTailoredCVResponse.model_validate(
            {
                "change_log": [{"change": "Improved wording."}],
                "tailoring_summary": "General polish.",
            }
        )


def test_cv_tailor_prompt_is_evidence_constrained_and_compact():
    prompt = build_cv_tailor_prompt()
    assert "LLM #3" in prompt
    assert "Never invent" in prompt
    assert "Do NOT repeat the CV" in prompt
    assert "at most 2" in prompt
    assert "at most 320 characters" in prompt


def test_cv_tailor_prompt_supports_general_enhancement_without_jd():
    prompt = build_cv_tailor_prompt(has_jd=False)
    assert "No Job Description is supplied" in prompt
    assert "without assuming a target role" in prompt


@pytest.mark.asyncio
async def test_tailor_cv_applies_llm_operation_and_derives_audit_log():
    source_cv = _sample_cv()
    with patch(
        "app.services.cv_tailor_service.call_llm_with_fallback",
        new_callable=AsyncMock,
        return_value=_sample_response(),
    ) as mock_call:
        result = await tailor_cv(source_cv, "Need a PyTorch engineer")

    assert result.response.tailored_cv["identity"] == source_cv["identity"]
    assert result.response.tailored_cv["experience"][0]["bullets"][0]["text"] == (
        "Built 2 PyTorch classification APIs."
    )
    assert result.response.change_log[0].original_text == "Built 2 PyTorch APIs."
    assert "Need a PyTorch engineer" in result.raw_prompt
    assert mock_call.await_args.kwargs["max_output_tokens"] == 768
    assert "result_validator" not in mock_call.await_args.kwargs


@pytest.mark.asyncio
async def test_tailor_cv_supports_general_enhancement_without_jd():
    source_cv = _sample_cv()
    with patch(
        "app.services.cv_tailor_service.call_llm_with_fallback",
        new_callable=AsyncMock,
        return_value=_sample_response(),
    ) as mock_call:
        result = await tailor_cv(source_cv)

    assert result.response.tailoring_summary
    assert "Not supplied. Perform a general CV enhancement audit." in result.raw_prompt
    assert (
        "without assuming a target role" in mock_call.await_args.kwargs["system_prompt"]
    )


@pytest.mark.asyncio
async def test_tailor_cv_discards_changed_numeric_evidence_without_failing_request():
    invalid = _sample_response()
    invalid.change_log[0].proposed_text = "Built 3 PyTorch APIs."
    with patch(
        "app.services.cv_tailor_service.call_llm_with_fallback",
        new_callable=AsyncMock,
        return_value=invalid,
    ):
        result = await tailor_cv(_sample_cv(), "Need a PyTorch engineer")

    assert result.response.change_log == []
    assert result.response.tailored_cv == _sample_cv()
    assert "No safe CV changes" in result.response.tailoring_summary


@pytest.mark.asyncio
async def test_tailor_cv_discards_unsupported_operation_path_without_failing_request():
    invalid = _sample_response()
    invalid.change_log[0].path = "skills.ML[0]"
    with patch(
        "app.services.cv_tailor_service.call_llm_with_fallback",
        new_callable=AsyncMock,
        return_value=invalid,
    ):
        result = await tailor_cv(_sample_cv(), "Need a PyTorch engineer")

    assert result.response.change_log == []
    assert result.response.tailored_cv == _sample_cv()


def test_llm3_contract_bounds_operation_count_and_text_length():
    operation = {
        "path": "experience[0].bullets[0].text",
        "proposed_text": "x" * 321,
        "rationale": "Short reason.",
    }
    with pytest.raises(ValidationError, match="at most 320 characters"):
        LLMTailoredCVResponse.model_validate(
            {"change_log": [operation], "tailoring_summary": "General polish."}
        )

    valid_operation = {**operation, "proposed_text": "Short rewrite."}
    with pytest.raises(ValidationError, match="at most 2 items"):
        LLMTailoredCVResponse.model_validate(
            {
                "change_log": [valid_operation, valid_operation, valid_operation],
                "tailoring_summary": "General polish.",
            }
        )
