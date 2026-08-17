"""Tests for isolated LLM #1 v2 source-atom mapper."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.models.cv_block_plan import (
    AtomEntryPlan,
    AtomIdentityPlan,
    AtomSectionPlan,
    LLMAtomPlanResponse,
    LLMSectionAtomPlanResponse,
)
from app.models.cv_raw_extraction import (
    ExtractionMethod,
    RawBlock,
    RawExtraction,
    RawPage,
)
from app.prompts.system_prompts import (
    build_block_plan_prompt,
    build_section_block_plan_prompt,
)
from app.services.cv_block_plan_service import (
    InvalidAtomPlanError,
    build_source_atoms,
    repeated_atom_ids,
    split_atoms_into_sections,
    structure_cv_block_plan,
    validate_atom_plan,
)


def _raw() -> RawExtraction:
    return RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[
            RawPage(
                page=1,
                blocks=[
                    RawBlock(
                        block_id="b1",
                        page=1,
                        text="Nguyen Duy",
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
                        text="Experience",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=2,
                    ),
                    RawBlock(
                        block_id="b4",
                        page=1,
                        text="Research Assistant",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=3,
                    ),
                    RawBlock(
                        block_id="b5",
                        page=1,
                        text="IoT Network Lab",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=4,
                    ),
                    RawBlock(
                        block_id="b6",
                        page=1,
                        text="• Built source-grounded mapper.",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=5,
                    ),
                ],
            )
        ],
    )


def _complete_plan(raw: RawExtraction) -> LLMAtomPlanResponse:
    ids = {atom.block_id: atom.atom_id for atom in build_source_atoms(raw)}
    return LLMAtomPlanResponse(
        identity=AtomIdentityPlan(
            full_name_atom_ids=[ids["b1"]],
            headline_atom_ids=[ids["b2"]],
        ),
        sections=[
            AtomSectionPlan(
                type="experience",
                title_atom_ids=[ids["b3"]],
                blocks=[
                    AtomEntryPlan(
                        type="entry",
                        title_atom_ids=[ids["b4"]],
                        organization_atom_ids=[ids["b5"]],
                        bullet_atom_id_groups=[[ids["b6"]]],
                    )
                ],
            )
        ],
    )


def test_block_plan_prompt_prohibits_candidate_text():
    prompt = build_block_plan_prompt()
    assert "MUST NOT output candidate wording" in prompt
    assert "Never guess a next/hidden ID" in prompt
    section_prompt = build_section_block_plan_prompt("education", "Education")
    assert "REQUIRED exactly once" in section_prompt
    assert "institution` is university/school/lab" in section_prompt


def test_source_atom_ids_are_short_deterministic_pointers():
    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[
            RawPage(
                page=2,
                blocks=[
                    RawBlock(
                        block_id="p2-b7",
                        page=2,
                        text="Source atom",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=0,
                    )
                ],
            )
        ],
    )

    assert [atom.atom_id for atom in build_source_atoms(raw)] == ["p2-b7:a1"]


def test_split_atoms_into_sections_uses_heading_boundaries_and_deterministic_header():
    raw = _raw()
    atoms = build_source_atoms(raw)

    identity, preamble, ranges = split_atoms_into_sections(atoms)

    assert identity.full_name_atom_ids == ["b1:a1"]
    assert identity.headline_atom_ids == ["b2:a1"]
    assert [atom.atom_id for atom in preamble] == ["b1:a1", "b2:a1"]
    assert [(section.type, section.title_atom.atom_id) for section in ranges] == [
        ("experience", "b3:a1")
    ]
    assert [atom.atom_id for atom in ranges[0].content_atoms] == [
        "b4:a1",
        "b5:a1",
        "b6:a1",
    ]


def test_block_plan_rejects_omitted_source_atom():
    raw = _raw()
    plan = _complete_plan(raw)
    plan.sections[0].blocks[0].bullet_atom_id_groups = []

    with pytest.raises(InvalidAtomPlanError, match="omitted source atoms"):
        validate_atom_plan(build_source_atoms(raw), plan)


def test_block_plan_schema_allows_repeated_semantic_references_for_audit():
    """Qwen may repeat an atom; service must inspect it instead of discarding JSON."""
    raw = _raw()
    plan = _complete_plan(raw)
    payload = plan.model_dump()
    payload["sections"][0]["title_atom_ids"].append(
        payload["identity"]["full_name_atom_ids"][0]
    )

    parsed = LLMAtomPlanResponse.model_validate(payload)

    assert (
        parsed.sections[0].title_atom_ids[-1] == parsed.identity.full_name_atom_ids[0]
    )
    assert repeated_atom_ids(parsed) == [parsed.identity.full_name_atom_ids[0]]


@pytest.mark.asyncio
async def test_block_plan_mapper_reconstructs_only_server_source_atoms():
    raw = _raw()
    ids = {atom.block_id: atom.atom_id for atom in build_source_atoms(raw)}
    section_plan = LLMSectionAtomPlanResponse(
        coverage_atom_ids=[ids["b4"], ids["b5"], ids["b6"]],
        blocks=[
            AtomEntryPlan(
                type="entry",
                title_atom_ids=[ids["b4"]],
                organization_atom_ids=[ids["b5"]],
                bullet_atom_id_groups=[[ids["b6"]]],
            )
        ],
    )

    with patch(
        "app.services.cv_block_plan_service.call_llm_with_fallback",
        new_callable=AsyncMock,
        return_value=section_plan,
    ) as mock_call:
        result = await structure_cv_block_plan(
            cv_text="ignored because raw source is explicit",
            raw_extraction=raw,
        )

    assert not result.used_fallback
    assert result.plan is not None
    assert result.document.parser_version == "llm-block-plan-2.0-experimental"
    assert not result.document.requires_reprocessing
    assert not result.document.reconstruction_warnings
    assert result.repeated_atom_ids == []
    entry = result.document.sections[0].blocks[0]
    assert entry.title == "Research Assistant"
    assert entry.organization == "IoT Network Lab"
    assert entry.bullets == ["Built source-grounded mapper."]
    assert mock_call.await_args.args[0] == build_section_block_plan_prompt(
        "experience",
        "Experience",
    )


@pytest.mark.asyncio
async def test_block_plan_duplicate_atoms_are_reported_not_discarded():
    raw = _raw()
    ids = {atom.block_id: atom.atom_id for atom in build_source_atoms(raw)}
    repeated = ids["b4"]
    plan = LLMSectionAtomPlanResponse(
        coverage_atom_ids=[ids["b4"], ids["b5"], ids["b6"]],
        blocks=[
            AtomEntryPlan(
                type="entry",
                title_atom_ids=[repeated],
                organization_atom_ids=[ids["b5"]],
                bullet_atom_id_groups=[[repeated], [ids["b6"]]],
            )
        ],
    )

    with patch(
        "app.services.cv_block_plan_service.call_llm_with_fallback",
        new_callable=AsyncMock,
        return_value=plan,
    ):
        result = await structure_cv_block_plan(
            cv_text="ignored because raw source is explicit",
            raw_extraction=raw,
        )

    assert not result.used_fallback
    assert result.repeated_atom_ids == [repeated]
    assert result.document.requires_reprocessing
    assert (
        "block_plan_duplicate_atom_reference" in result.document.reconstruction_warnings
    )


@pytest.mark.asyncio
async def test_block_plan_unknown_atoms_are_removed_before_document_assembly():
    raw = _raw()
    ids = {atom.block_id: atom.atom_id for atom in build_source_atoms(raw)}
    forged = "p2-b49:a1"
    plan = LLMSectionAtomPlanResponse(
        coverage_atom_ids=[ids["b4"], ids["b5"], ids["b6"]],
        blocks=[
            AtomEntryPlan(
                type="entry",
                title_atom_ids=[ids["b4"]],
                organization_atom_ids=[ids["b5"]],
                bullet_atom_id_groups=[[ids["b6"]], [forged]],
            )
        ],
    )

    with patch(
        "app.services.cv_block_plan_service.call_llm_with_fallback",
        new_callable=AsyncMock,
        return_value=plan,
    ):
        result = await structure_cv_block_plan(
            cv_text="ignored because raw source is explicit",
            raw_extraction=raw,
        )

    assert not result.used_fallback
    assert result.unknown_atom_ids == []
    assert not result.document.requires_reprocessing


@pytest.mark.asyncio
async def test_bad_section_receives_one_targeted_repair_and_uses_better_plan():
    raw = _raw()
    ids = {atom.block_id: atom.atom_id for atom in build_source_atoms(raw)}
    incomplete = LLMSectionAtomPlanResponse(
        coverage_atom_ids=[ids["b4"], ids["b5"], ids["b6"]],
        blocks=[
            AtomEntryPlan(
                type="entry",
                title_atom_ids=[ids["b4"]],
                organization_atom_ids=[ids["b5"]],
            )
        ],
    )
    repaired = LLMSectionAtomPlanResponse(
        coverage_atom_ids=[ids["b4"], ids["b5"], ids["b6"]],
        blocks=[
            AtomEntryPlan(
                type="entry",
                title_atom_ids=[ids["b4"]],
                organization_atom_ids=[ids["b5"]],
                bullet_atom_id_groups=[[ids["b6"]]],
            )
        ],
    )

    with patch(
        "app.services.cv_block_plan_service.call_llm_with_fallback",
        new_callable=AsyncMock,
        side_effect=[incomplete, repaired],
    ) as mock_call:
        result = await structure_cv_block_plan(
            cv_text="ignored because raw source is explicit",
            raw_extraction=raw,
        )

    assert mock_call.await_count == 2
    assert "REPAIR REQUIRED" in mock_call.await_args.args[0]
    assert not result.missing_atom_ids
    assert not result.repeated_atom_ids
    assert not result.document.requires_reprocessing


@pytest.mark.asyncio
async def test_invalid_section_response_falls_back_only_for_that_section():
    raw = _raw()

    with patch(
        "app.services.cv_block_plan_service.call_llm_with_fallback",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=502, detail="truncated JSON"),
    ):
        result = await structure_cv_block_plan(
            cv_text="ignored because raw source is explicit",
            raw_extraction=raw,
        )

    assert result.used_fallback
    assert result.section_fallback_types == ["experience"]
    assert result.plan is not None
    assert not result.missing_atom_ids
    assert result.document.sections[0].blocks[0].type == "unknown"
    assert "block_plan_section_fallback" in result.document.reconstruction_warnings
