"""Tests for isolated LLM #1 v3.1 cursor-plan mapper."""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import CV_RANGE_PLAN_SECTION_MAX_OUTPUT_TOKENS
from app.models.cv_range_plan import LLMSectionCursorPlanResponse
from app.models.cv_raw_extraction import (
    ExtractionMethod,
    RawBlock,
    RawExtraction,
    RawPage,
)
from app.prompts.system_prompts import (
    build_section_range_plan_prompt,
    build_visual_entry_header_prompt,
    format_source_ledger,
    format_visual_entry_header,
)
from app.services.cv_range_plan_service import (
    InvalidRangePlanError,
    _LedgerSection,
    _plan_section,
    _visual_entry_header_positions,
    build_source_ledger,
    compile_section_cursor_plan,
    structure_cv_range_plan,
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
                        text="Soonchunhyang University – IoT Network Lab",
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


def _plan() -> LLMSectionCursorPlanResponse:
    return LLMSectionCursorPlanResponse.model_validate(
        {"b": [{"k": "e", "s": [["t", 1], ["o", 1], ["b", 1]]}]}
    )


def test_v31_ledger_has_server_offsets_not_model_identifiers():
    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[
            RawPage(
                page=1,
                blocks=[
                    RawBlock(
                        block_id="b1",
                        page=1,
                        text="Python | PyTorch",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=0,
                    )
                ],
            )
        ],
    )

    ledger = build_source_ledger(raw)

    assert [
        (atom.index, atom.text, atom.start_offset, atom.end_offset) for atom in ledger
    ] == [(0, "Python", 0, 6), (1, "PyTorch", 9, 16)]


def test_v31_compact_cursor_json_has_no_model_positions_or_text_fields():
    plan = _plan()

    assert plan.model_dump(by_alias=True) == {
        "b": [{"k": "e", "s": [("t", 1), ("o", 1), ("b", 1)]}]
    }


def test_v31_cursor_requires_exact_total_and_splits_repeated_education_anchor():
    ledger = build_source_ledger(_raw())
    section = _LedgerSection(type="education", title=ledger[2], content=ledger[3:])
    plan = LLMSectionCursorPlanResponse.model_validate(
        {"b": [{"k": "d", "s": [["i", 1], ["t", 1], ["i", 1]]}]}
    )

    blocks = compile_section_cursor_plan(section, plan)

    assert [[role for role, _ in block.fields] for block in blocks] == [
        ["i", "t"],
        ["i"],
    ]

    short = LLMSectionCursorPlanResponse.model_validate(
        {"b": [{"k": "d", "s": [["i", 1]]}]}
    )
    short_blocks = compile_section_cursor_plan(section, short)
    assert len(short_blocks) == 1
    assert short_blocks[0].fields[0][0] == "i"
    assert len(short_blocks[0].fields[1][1]) == 2


@pytest.mark.asyncio
async def test_v31_renders_only_server_owned_cursor_text():
    with patch(
        "app.services.cv_range_plan_service.call_llm_with_fallback",
        new_callable=AsyncMock,
        return_value=_plan(),
    ) as mock_call:
        result = await structure_cv_range_plan(cv_text="ignored", raw_extraction=_raw())

    assert not result.used_fallback
    assert result.ledger_atom_count == 6
    assert result.unclassified_atom_indexes == []
    assert result.document.parser_version == "llm-cursor-plan-3.2-experimental-geometry"
    entry = result.document.sections[0].blocks[0]
    assert entry.title == "Research Assistant"
    assert entry.organization == "Soonchunhyang University – IoT Network Lab"
    assert entry.bullets == ["Built source-grounded mapper."]
    assert mock_call.await_args.args[0] == build_section_range_plan_prompt(
        "experience", "Experience", atom_count=3
    )
    assert (
        mock_call.await_args.kwargs["max_output_tokens"]
        == CV_RANGE_PLAN_SECTION_MAX_OUTPUT_TOKENS
    )


@pytest.mark.asyncio
async def test_v31_keeps_other_sections_when_one_plan_fails():
    failed = InvalidRangePlanError("bad local plan")
    with patch(
        "app.services.cv_range_plan_service.call_llm_with_fallback",
        new_callable=AsyncMock,
        side_effect=failed,
    ):
        result = await structure_cv_range_plan(cv_text="ignored", raw_extraction=_raw())

    assert not result.used_fallback
    assert result.section_failures == ["experience"]
    assert "cursor_plan_unclassified_source" in result.document.reconstruction_warnings
    assert result.document.sections[0].blocks[0].type == "unknown"


def test_v32_preserves_two_visual_header_rows_for_entry_field_labelling():
    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[
            RawPage(
                page=1,
                width=612,
                blocks=[
                    RawBlock(
                        block_id="b1",
                        page=1,
                        text="Experience",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=0,
                        bbox=(40, 350, 160, 362),
                    ),
                    RawBlock(
                        block_id="b2",
                        page=1,
                        text="Zalo – VNG Corporation",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=1,
                        bbox=(40, 384, 166, 394),
                    ),
                    RawBlock(
                        block_id="b3",
                        page=1,
                        text="Ho Chi Minh City, Vietnam",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=2,
                        bbox=(459, 385, 572, 394),
                    ),
                    RawBlock(
                        block_id="b4",
                        page=1,
                        text="Software Engineer, Zalo PC",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=3,
                        bbox=(40, 397, 152, 406),
                    ),
                    RawBlock(
                        block_id="b5",
                        page=1,
                        text="May 2022 – Mar 2024",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=4,
                        bbox=(482, 397, 572, 406),
                    ),
                    RawBlock(
                        block_id="b6",
                        page=1,
                        text="– Shipped production features.",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=5,
                        bbox=(51, 416, 508, 426),
                    ),
                ],
            )
        ],
    )
    ledger = build_source_ledger(raw)
    section = _LedgerSection(type="experience", title=ledger[0], content=ledger[1:])
    header_positions = _visual_entry_header_positions(section)

    formatted = format_source_ledger(
        section.content,
        visual_entry_header_positions=header_positions,
    )

    assert header_positions == {0, 1, 2, 3}
    assert "[ENTRY HEADER row=1 col=L] 0: Zalo – VNG Corporation" in formatted
    assert "[ENTRY HEADER row=1 col=R] 1: Ho Chi Minh City, Vietnam" in formatted
    assert "[ENTRY HEADER row=2 col=L] 2: Software Engineer, Zalo PC" in formatted
    assert "[ENTRY HEADER row=2 col=R] 3: May 2022 – Mar 2024" in formatted
    assert (
        build_section_range_plan_prompt(
            "experience", "Experience", has_visual_entry_header=True
        ).count("company/lab and location")
        == 1
    )


@pytest.mark.asyncio
async def test_v32_visual_header_task_overrides_section_planner_roles():
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
                        bbox=(40, 350, 160, 362),
                    ),
                    RawBlock(
                        block_id="b2",
                        page=1,
                        text="Zalo – VNG Corporation",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=1,
                        bbox=(40, 384, 166, 394),
                    ),
                    RawBlock(
                        block_id="b3",
                        page=1,
                        text="Ho Chi Minh City, Vietnam",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=2,
                        bbox=(459, 385, 572, 394),
                    ),
                    RawBlock(
                        block_id="b4",
                        page=1,
                        text="Software Engineer, Zalo PC",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=3,
                        bbox=(40, 397, 152, 406),
                    ),
                    RawBlock(
                        block_id="b5",
                        page=1,
                        text="May 2022 – Mar 2024",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=4,
                        bbox=(482, 397, 572, 406),
                    ),
                    RawBlock(
                        block_id="b6",
                        page=1,
                        text="– Shipped production features.",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=5,
                        bbox=(51, 416, 508, 426),
                    ),
                ],
            )
        ],
    )
    ledger = build_source_ledger(raw)
    section = _LedgerSection(type="experience", title=ledger[0], content=ledger[1:])
    header_response = {"r": ["o", "l", "t", "d"]}
    section_response = {
        "b": [{"k": "e", "s": [["t", 1], ["l", 1], ["o", 1], ["d", 1], ["b", 1]]}]
    }

    with patch(
        "app.services.cv_range_plan_service.call_llm_with_fallback",
        new_callable=AsyncMock,
        side_effect=[header_response, section_response],
    ) as mock_call:
        blocks = await _plan_section(section, background_tasks=None, on_retry=None)

    assert mock_call.await_args_list[0].args[0] == build_visual_entry_header_prompt(
        "Experience"
    )
    assert mock_call.await_args_list[0].args[1] == format_visual_entry_header(
        section.content[:4]
    )
    fields = {
        role: atoms[0].text for role, atoms in blocks[0].fields if len(atoms) == 1
    }
    assert fields["o"] == "Zalo – VNG Corporation"
    assert fields["l"] == "Ho Chi Minh City, Vietnam"
    assert fields["t"] == "Software Engineer, Zalo PC"
    assert fields["d"] == "May 2022 – Mar 2024"


def test_v31_tail_bullet_count_auto_absorption():
    ledger = build_source_ledger(_raw())
    # 3 content atoms: Research Assistant, Soonchunhyang University, • Built source-grounded mapper.
    section = _LedgerSection(type="experience", title=ledger[2], content=ledger[3:])

    # LLM incorrectly returns count=13 for bullets instead of 1
    plan = LLMSectionCursorPlanResponse.model_validate(
        {"b": [{"k": "e", "s": [["t", 1], ["o", 1], ["b", 13]]}]}
    )
    blocks = compile_section_cursor_plan(section, plan)
    assert len(blocks) == 1
    assert blocks[0].fields[-1][0] == "b"
    # Auto-clamped to consume remaining 1 atom
    assert len(blocks[0].fields[-1][1]) == 1
    assert blocks[0].fields[-1][1][0].text == "Built source-grounded mapper."


@pytest.mark.asyncio
async def test_v31_parallel_section_structure_preserves_order():
    raw = RawExtraction(
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
                        text="Soonchunhyang University – IoT Network Lab",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=4,
                    ),
                    RawBlock(
                        block_id="b6",
                        page=1,
                        text="Education",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=5,
                    ),
                    RawBlock(
                        block_id="b7",
                        page=1,
                        text="Soonchunhyang University",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=6,
                    ),
                    RawBlock(
                        block_id="b8",
                        page=1,
                        text="M.S. in Engineering",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=7,
                    ),
                ],
            )
        ],
    )
    exp_plan = {"b": [{"k": "e", "s": [["t", 1], ["o", 1]]}]}
    edu_plan = {"b": [{"k": "d", "s": [["i", 1], ["t", 1]]}]}

    with patch(
        "app.services.cv_range_plan_service.call_llm_with_fallback",
        new_callable=AsyncMock,
        side_effect=[exp_plan, edu_plan],
    ):
        result = await structure_cv_range_plan(cv_text="ignored", raw_extraction=raw)

    assert not result.used_fallback
    assert len(result.document.sections) == 2
    assert result.document.sections[0].type == "experience"
    assert result.document.sections[1].type == "education"
