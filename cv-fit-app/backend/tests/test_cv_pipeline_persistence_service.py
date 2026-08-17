"""Tests for saving a bounded LLM #3 delta as an exportable CV version."""

from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest

from app.models.cv_document_v2 import (
    ContentOrigin,
    CVDocumentV2,
    CVEntryBlock,
    CVIdentity,
    CVSection,
)
from app.models.cv_raw_extraction import RawBlock, RawExtraction, RawPage
from app.models.cv_tailoring import TailoredCVResponse, TailoringChangeItem
from app.services.cv_pipeline_persistence_service import persist_pipeline_tailoring


def _source_document() -> CVDocumentV2:
    return CVDocumentV2(
        identity=CVIdentity(full_name="Lan Nguyen"),
        sections=[
            CVSection(
                type="experience",
                title="Experience",
                source_block_ids=["b1"],
                blocks=[
                    CVEntryBlock(
                        block_id="b1",
                        title="ML Engineer",
                        bullets=["Built 2 PyTorch APIs."],
                        source_block_ids=["b1"],
                        origin=ContentOrigin.EXTRACTED,
                    )
                ],
            )
        ],
    )


def _raw_extraction() -> RawExtraction:
    return RawExtraction(
        method="native_blocks",
        pages=[
            RawPage(
                page=1,
                blocks=[
                    RawBlock(
                        block_id="b1",
                        page=1,
                        text="Built 2 PyTorch APIs for classification.",
                        extraction_method="native_blocks",
                    )
                ],
            )
        ],
    )


@pytest.mark.asyncio
async def test_persist_pipeline_tailoring_maps_and_validates_llm3_bullet_delta():
    tailoring = TailoredCVResponse(
        tailored_cv={},
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
    saved = object()
    with (
        patch(
            "app.services.cv_pipeline_persistence_service.validate_reconstruction_gate"
        ),
        patch(
            "app.services.cv_pipeline_persistence_service.verify_block_rewrite_semantics_with_validator",
            new_callable=AsyncMock,
            return_value=(True, []),
        ),
        patch(
            "app.services.cv_pipeline_persistence_service.create_version",
            new_callable=AsyncMock,
            return_value=saved,
        ) as create_version,
    ):
        result = await persist_pipeline_tailoring(
            user_id=UUID("11111111-1111-4111-8111-111111111111"),
            source_text="Lan Nguyen\nBuilt 2 PyTorch APIs for classification.",
            raw_extraction=_raw_extraction(),
            source_document=_source_document(),
            job_description=None,
            tailoring=tailoring,
            analysis_key="analysis-key",
        )

    assert result is saved
    request = create_version.await_args.args[1]
    assert request.document_v2.sections[0].blocks[0].bullets == [
        "Built 2 PyTorch classification APIs."
    ]
    assert request.tailoring_diagnostics.accepted_count == 1
    assert request.tailoring_diagnostics.preserved_count == 0
    assert request.jd_text == ""
