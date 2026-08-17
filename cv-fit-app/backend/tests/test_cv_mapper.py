"""Tests for LLM #1 — CV Mapper (Semantic CV Structuring & Canonical CV Export)."""

from unittest.mock import AsyncMock, patch

import pytest

from app.models.cv_document_v2 import (
    CVDocumentV2,
    CVEducationBlock,
    CVEntryBlock,
    CVIdentity,
    CVParagraphBlock,
    CVSection,
    CVSkillGroupBlock,
)
from app.models.cv_raw_extraction import (
    ExtractionMethod,
    RawBlock,
    RawExtraction,
    RawPage,
)
from app.models.cv_structuring import (
    LLMEntryBlock,
    LLMIdentityCandidate,
    LLMIdentitySourceMap,
    LLMSectionCandidate,
    LLMSemanticCVResponse,
    LLMSummaryCandidate,
    LLMUnmappedCandidate,
)
from app.prompts.system_prompts import build_block_parsing_prompt
from app.services.cv_structuring_service import structure_cv


def test_llm1_prompt_is_strictly_mapper_only():
    """Verify LLM #1 prompt is focused strictly on mapping without judgment."""
    prompt = build_block_parsing_prompt()
    assert "LLM #1" in prompt
    assert "DO NOT evaluate candidate fit" in prompt
    assert (
        "Understand what this CV says and organize it into a predictable JSON structure"
        in prompt
    )


def test_cv_document_v2_to_canonical_dict():
    """Test exporting CVDocumentV2 to normalized machine-readable CV JSON."""
    doc = CVDocumentV2(
        identity=CVIdentity(
            full_name="Nguyen Thanh Minh Duy",
            headline="AI Engineer / ML Engineer",
            email="ntminhduy123@gmail.com",
            phone="+84 33-545-2060",
            location="Ho Chi Minh City, Vietnam",
            links=["https://github.com/ntminhduy123"],
        ),
        summary=CVParagraphBlock(
            text="AI and machine learning researcher building career SaaS platforms.",
            source_block_ids=["b3"],
        ),
        sections=[
            CVSection(
                id="sec-1",
                type="education",
                title="Education",
                source_block_ids=["b10"],
                blocks=[
                    CVEducationBlock(
                        institution="Soonchunhyang University (SCH)",
                        degree="M.S. in Engineering (Fully Funded)",
                        location="South Korea",
                        date="Mar 2024 – Feb 2026",
                        details=["Focus: Deep Learning, Few-Shot Learning"],
                        source_block_ids=["b10"],
                    )
                ],
            ),
            CVSection(
                id="sec-2",
                type="experience",
                title="Experience",
                source_block_ids=["b15"],
                blocks=[
                    CVEntryBlock(
                        title="Independent Builder",
                        organization="Bé Đậu – AI Career SaaS",
                        date="2025 – Present",
                        bullets=[
                            "Built an AI career platform...",
                            "Designed a FastAPI backend...",
                        ],
                        source_block_ids=["b15"],
                    )
                ],
            ),
            CVSection(
                id="sec-3",
                type="skills",
                title="Skills",
                source_block_ids=["b20"],
                blocks=[
                    CVSkillGroupBlock(
                        label="AI Engineering",
                        skills=["PyTorch", "FastAPI", "Transformers"],
                        source_block_ids=["b20"],
                    )
                ],
            ),
        ],
    )

    canonical = doc.to_canonical_dict()

    assert canonical["identity"]["name"] == "Nguyen Thanh Minh Duy"
    assert canonical["identity"]["headline"] == "AI Engineer / ML Engineer"
    assert canonical["identity"]["email"] == "ntminhduy123@gmail.com"
    assert (
        canonical["summary"]
        == "AI and machine learning researcher building career SaaS platforms."
    )

    assert len(canonical["education"]) == 1
    assert canonical["education"][0]["institution"] == "Soonchunhyang University (SCH)"
    assert canonical["education"][0]["degree"] == "M.S. in Engineering (Fully Funded)"

    assert len(canonical["experience"]) == 1
    assert canonical["experience"][0]["title"] == "Independent Builder"
    assert canonical["experience"][0]["organization"] == "Bé Đậu – AI Career SaaS"
    assert len(canonical["experience"][0]["bullets"]) == 2
    assert (
        canonical["experience"][0]["bullets"][0]["text"]
        == "Built an AI career platform..."
    )
    assert canonical["experience"][0]["bullets"][0]["source"] == ["b15"]

    assert canonical["skills"]["AI Engineering"] == [
        "PyTorch",
        "FastAPI",
        "Transformers",
    ]


@pytest.mark.asyncio
async def test_structure_cv_invokes_llm1_mapper():
    """Test LLM #1 service call produces structured result and canonical JSON."""
    raw_blocks = [
        RawBlock(
            block_id="b1",
            page=1,
            text="Nguyen Thanh Minh Duy",
            extraction_method=ExtractionMethod.NATIVE_BLOCKS,
            reading_order=0,
        ),
        RawBlock(
            block_id="b2",
            page=1,
            text="AI Engineer | ntminhduy123@gmail.com",
            extraction_method=ExtractionMethod.NATIVE_BLOCKS,
            reading_order=1,
        ),
        RawBlock(
            block_id="b3",
            page=1,
            text="Experienced AI developer building ML solutions.",
            extraction_method=ExtractionMethod.NATIVE_BLOCKS,
            reading_order=2,
        ),
    ]
    raw_extraction = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[RawPage(page=1, blocks=raw_blocks)],
    )

    mock_llm_response = LLMSemanticCVResponse(
        identity=LLMIdentityCandidate(
            full_name="Nguyen Thanh Minh Duy",
            headline="AI Engineer",
            email="ntminhduy123@gmail.com",
            field_source_block_ids=LLMIdentitySourceMap(
                full_name=["b1"],
                headline=["b2"],
                email=["b2"],
            ),
        ),
        summary=LLMSummaryCandidate(
            text="Experienced AI developer building ML solutions.",
            source_block_ids=["b3"],
        ),
        sections=[],
    )

    with (
        patch(
            "app.services.cv_structuring_service.resolve_authoritative_source",
            new_callable=AsyncMock,
        ) as mock_res,
        patch(
            "app.services.cv_structuring_service.call_llm_with_fallback",
            new_callable=AsyncMock,
        ) as mock_call,
    ):
        mock_res.return_value = (
            raw_extraction,
            "Nguyen Thanh Minh Duy\nAI Engineer | ntminhduy123@gmail.com\nExperienced AI developer building ML solutions.",
        )
        mock_call.return_value = mock_llm_response

        result = await structure_cv(cv_text="Nguyen Thanh Minh Duy...")

        assert result.used_fallback is False
        assert result.document.identity.full_name == "Nguyen Thanh Minh Duy"
        assert result.document.identity.email == "ntminhduy123@gmail.com"
        assert (
            result.document.summary.text
            == "Experienced AI developer building ML solutions."
        )

        canonical = result.document.to_canonical_dict()
        assert canonical["identity"]["name"] == "Nguyen Thanh Minh Duy"
        assert canonical["summary"] == "Experienced AI developer building ML solutions."


@pytest.mark.asyncio
async def test_structure_cv_repairs_omitted_exact_block_citation():
    raw_blocks = [
        RawBlock(
            block_id="b1",
            page=1,
            text="Experience",
            extraction_method=ExtractionMethod.NATIVE_BLOCKS,
            reading_order=0,
        ),
        RawBlock(
            block_id="b2",
            page=1,
            text="AI Engineer",
            extraction_method=ExtractionMethod.NATIVE_BLOCKS,
            reading_order=1,
        ),
        RawBlock(
            block_id="b3",
            page=1,
            text="Built exact-source software.",
            extraction_method=ExtractionMethod.NATIVE_BLOCKS,
            reading_order=2,
        ),
    ]
    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[RawPage(page=1, blocks=raw_blocks)],
    )
    response = LLMSemanticCVResponse(
        sections=[
            LLMSectionCandidate(
                type="experience",
                title="Experience",
                source_block_ids=["b1"],
                blocks=[
                    LLMEntryBlock(
                        type="entry",
                        title="AI Engineer",
                        bullets=["Built exact-source software."],
                        source_block_ids=["b2"],
                    )
                ],
            )
        ]
    )

    with (
        patch(
            "app.services.cv_structuring_service.resolve_authoritative_source",
            new_callable=AsyncMock,
        ) as mock_res,
        patch(
            "app.services.cv_structuring_service.call_llm_with_fallback",
            new_callable=AsyncMock,
        ) as mock_call,
    ):
        mock_res.return_value = (
            raw,
            "Experience\nAI Engineer\nBuilt exact-source software.",
        )
        mock_call.return_value = response

        result = await structure_cv(cv_text="ignored")

    block = result.document.sections[0].blocks[0]
    assert block.source_block_ids == ["b2", "b3"]


@pytest.mark.asyncio
async def test_structure_cv_discards_redundant_unmapped_marker_for_mapped_block():
    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[
            RawPage(
                page=1,
                blocks=[
                    RawBlock(
                        block_id="b1",
                        page=1,
                        text="Summary",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=0,
                    ),
                    RawBlock(
                        block_id="b2",
                        page=1,
                        text="Built source-grounded software.",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=1,
                    ),
                ],
            )
        ],
    )
    response = LLMSemanticCVResponse(
        summary=LLMSummaryCandidate(
            text="Built source-grounded software.",
            source_block_ids=["b2"],
        ),
        unmapped_references=[
            LLMUnmappedCandidate(block_id="b2", reason="ambiguous_content")
        ],
    )

    with (
        patch(
            "app.services.cv_structuring_service.resolve_authoritative_source",
            new_callable=AsyncMock,
            return_value=(raw, "Summary\nBuilt source-grounded software."),
        ),
        patch(
            "app.services.cv_structuring_service.call_llm_with_fallback",
            new_callable=AsyncMock,
            return_value=response,
        ),
    ):
        result = await structure_cv(cv_text="ignored")

    assert not result.used_fallback
    assert result.document.summary.text == "Built source-grounded software."
    assert all(item.block_id != "b2" for item in result.document.unmapped_content)


@pytest.mark.asyncio
async def test_structure_cv_retries_verbatim_grounding_repair():
    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[
            RawPage(
                page=1,
                blocks=[
                    RawBlock(
                        block_id="b1",
                        page=1,
                        text="Experience",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=0,
                    ),
                    RawBlock(
                        block_id="b2",
                        page=1,
                        text="AI Engineer",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=1,
                    ),
                    RawBlock(
                        block_id="b3",
                        page=1,
                        text="Built source-backed software.",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=2,
                    ),
                ],
            )
        ],
    )
    invalid = LLMSemanticCVResponse(
        sections=[
            LLMSectionCandidate(
                type="experience",
                title="Experience",
                source_block_ids=["b1"],
                blocks=[
                    LLMEntryBlock(
                        type="entry",
                        title="AI Engineer",
                        bullets=["Built reliable software."],
                        source_block_ids=["b2", "b3"],
                    )
                ],
            )
        ]
    )
    corrected = invalid.model_copy(deep=True)
    corrected.sections[0].blocks[0].bullets = ["Built source-backed software."]

    with (
        patch(
            "app.services.cv_structuring_service.resolve_authoritative_source",
            new_callable=AsyncMock,
            return_value=(
                raw,
                "Experience\nAI Engineer\nBuilt source-backed software.",
            ),
        ),
        patch(
            "app.services.cv_structuring_service.call_llm_with_fallback",
            new_callable=AsyncMock,
            side_effect=[invalid, corrected],
        ) as mock_call,
    ):
        result = await structure_cv(cv_text="ignored")

    assert result.used_fallback is False
    assert mock_call.await_count == 2
    repair_prompt = mock_call.await_args_list[1].args[0]
    repair_input = mock_call.await_args_list[1].args[1]
    assert "GROUNDING REPAIR" in repair_prompt
    assert "sections[0].blocks[0].bullets[0]" in repair_input


@pytest.mark.asyncio
async def test_structure_cv_recovers_near_verbatim_bullet_from_cited_source():
    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[
            RawPage(
                page=1,
                blocks=[
                    RawBlock(
                        block_id="b1",
                        page=1,
                        text="Experience",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=0,
                    ),
                    RawBlock(
                        block_id="b2",
                        page=1,
                        text="AI Engineer",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=1,
                    ),
                    RawBlock(
                        block_id="b3",
                        page=1,
                        text="Built source-backed software.",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=2,
                    ),
                ],
            )
        ],
    )
    response = LLMSemanticCVResponse(
        sections=[
            LLMSectionCandidate(
                type="experience",
                title="Experience",
                source_block_ids=["b1"],
                blocks=[
                    LLMEntryBlock(
                        type="entry",
                        title="AI Engineer",
                        bullets=["Built source backed software"],
                        source_block_ids=["b2", "b3"],
                    )
                ],
            )
        ]
    )

    with (
        patch(
            "app.services.cv_structuring_service.resolve_authoritative_source",
            new_callable=AsyncMock,
            return_value=(
                raw,
                "Experience\nAI Engineer\nBuilt source-backed software.",
            ),
        ),
        patch(
            "app.services.cv_structuring_service.call_llm_with_fallback",
            new_callable=AsyncMock,
            return_value=response,
        ) as mock_call,
    ):
        result = await structure_cv(cv_text="ignored")

    assert result.used_fallback is False
    assert mock_call.await_count == 1
    assert result.document.sections[0].blocks[0].bullets == [
        "Built source-backed software."
    ]


@pytest.mark.asyncio
async def test_structure_cv_recovers_paraphrased_summary_from_cited_source():
    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[
            RawPage(
                page=1,
                blocks=[
                    RawBlock(
                        block_id="b1",
                        page=1,
                        text="AI engineer with hands-on PyTorch experience.",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=0,
                    ),
                    RawBlock(
                        block_id="b2",
                        page=1,
                        text="Built automated experimentation pipelines.",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=1,
                    ),
                ],
            )
        ],
    )
    response = LLMSemanticCVResponse(
        summary=LLMSummaryCandidate(
            text="AI specialist experienced in ML experimentation.",
            source_block_ids=["b1", "b2"],
        )
    )

    with (
        patch(
            "app.services.cv_structuring_service.resolve_authoritative_source",
            new_callable=AsyncMock,
            return_value=(
                raw,
                "AI engineer with hands-on PyTorch experience.\n"
                "Built automated experimentation pipelines.",
            ),
        ),
        patch(
            "app.services.cv_structuring_service.call_llm_with_fallback",
            new_callable=AsyncMock,
            return_value=response,
        ) as mock_call,
    ):
        result = await structure_cv(cv_text="ignored")

    assert result.used_fallback is False
    assert mock_call.await_count == 1
    assert result.document.summary.text == (
        "AI engineer with hands-on PyTorch experience. "
        "Built automated experimentation pipelines."
    )


def test_exact_citation_repair_handles_wrapped_pdf_bullets():
    from app.services.cv_structuring_service import _exact_source_ids_for_value

    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[
            RawPage(
                page=1,
                blocks=[
                    RawBlock(
                        block_id=f"b{index}",
                        page=1,
                        text=text,
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=index,
                    )
                    for index, text in enumerate(
                        ["Built", "a", "fully", "grounded", "CV", "pipeline."],
                        start=1,
                    )
                ],
            ),
        ],
    )

    assert _exact_source_ids_for_value(raw, "Built a fully grounded CV pipeline.") == [
        "b1",
        "b2",
        "b3",
        "b4",
        "b5",
        "b6",
    ]


@pytest.mark.asyncio
async def test_structure_cv_repairs_omitted_exact_identity_link_citation():
    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[
            RawPage(
                page=1,
                blocks=[
                    RawBlock(
                        block_id="identity-links",
                        page=1,
                        text="LinkedIn: https://linkedin.com/in/example",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=1,
                    ),
                ],
            ),
        ],
    )
    response = LLMSemanticCVResponse(
        identity=LLMIdentityCandidate(links=["LinkedIn"]),
    )

    with (
        patch(
            "app.services.cv_structuring_service.resolve_authoritative_source",
            new_callable=AsyncMock,
        ) as mock_res,
        patch(
            "app.services.cv_structuring_service.call_llm_with_fallback",
            new_callable=AsyncMock,
        ) as mock_call,
    ):
        mock_res.return_value = (raw, "LinkedIn: https://linkedin.com/in/example")
        mock_call.return_value = response
        result = await structure_cv(cv_text="ignored")

    assert result.used_fallback is False
    assert result.document.identity.field_source_block_ids.links == {
        "LinkedIn": ["identity-links"],
    }


def test_certifications_date_merging():
    """Test that orphan date blocks in certifications are merged into the preceding certification entry."""
    doc = CVDocumentV2(
        sections=[
            CVSection(
                id="sec-cert",
                type="certifications",
                title="Certifications",
                source_block_ids=["b37", "b38"],
                blocks=[
                    CVEntryBlock(
                        title="Generative AI Engineering with LLMs Specialization",
                        organization="IBM",
                        date=None,
                        source_block_ids=["b37"],
                    ),
                    CVEntryBlock(
                        title="Mar 2026",
                        organization=None,
                        date="Mar 2026",
                        source_block_ids=["b38"],
                    ),
                ],
            )
        ]
    )

    canonical = doc.to_canonical_dict()
    certifications = canonical["certifications"]

    assert len(certifications) == 1
    assert (
        certifications[0]["title"]
        == "Generative AI Engineering with LLMs Specialization"
    )
    assert certifications[0]["organization"] == "IBM"
    assert certifications[0]["date"] == "Mar 2026"
    assert certifications[0]["source"] == ["b37", "b38"]


def test_cventryblock_prevents_location_title_swap():
    """Test that geographic locations like 'Asan, South Korea' are automatically moved from title to location."""
    entry = CVEntryBlock(
        title="Asan, South Korea",
        organization="Soonchunhyang University – IoT Network Lab",
        subtitle="Graduate Research Assistant",
        source_block_ids=["b1"],
    )
    assert entry.location == "Asan, South Korea"
    assert entry.title == "Graduate Research Assistant"
    assert entry.organization == "Soonchunhyang University – IoT Network Lab"
