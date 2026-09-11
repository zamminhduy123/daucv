"""Tests for isolated LLM #1 v3.1 cursor-plan mapper."""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import CV_RANGE_PLAN_SECTION_MAX_OUTPUT_TOKENS
from app.models.cv_range_plan import LLMSectionCursorPlanResponse, SourceLedgerAtom
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
    _build_identity,
    _LedgerSection,
    _looks_like_name,
    _plan_section,
    _render_block,
    _ResolvedBlock,
    _visual_entry_header_positions,
    build_source_ledger,
    compile_section_cursor_plan,
    structure_cv_range_plan,
)
from app.services.layout_extraction import join_logical_blocks


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

    blocks, clamped = compile_section_cursor_plan(section, plan)

    assert [[role for role, _ in block.fields] for block in blocks] == [
        ["i", "t"],
        ["i"],
    ]
    assert clamped is False

    short = LLMSectionCursorPlanResponse.model_validate(
        {"b": [{"k": "d", "s": [["i", 1]]}]}
    )
    short_blocks, short_clamped = compile_section_cursor_plan(section, short)
    assert len(short_blocks) == 1
    assert short_blocks[0].fields[0][0] == "i"
    assert len(short_blocks[0].fields[1][1]) == 2
    assert short_clamped is True


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
    assert result.document.parser_version == "llm-cursor-plan-3.3-logical-blocks"
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

    assert header_positions == {0, 1, 3, 4}
    assert "[ENTRY HEADER row=1 col=L] 0: Zalo – VNG Corporation" in formatted
    assert "[ENTRY HEADER row=2 col=L] 1: Software Engineer, Zalo PC" in formatted
    assert "[ENTRY HEADER row=1 col=R] 3: Ho Chi Minh City, Vietnam" in formatted
    assert "[ENTRY HEADER row=2 col=R] 4: May 2022 – Mar 2024" in formatted
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
    header_positions = _visual_entry_header_positions(section)
    header_response = {"r": ["o", "l", "t", "d"]}
    # Column-major reading order: [Zalo(t), Software(l), Shipped(o), HCMC(d), May2022(b)]
    section_response = {
        "b": [{"k": "e", "s": [["t", 1], ["l", 1], ["o", 1], ["d", 1], ["b", 1]]}]
    }

    with patch(
        "app.services.cv_range_plan_service.call_llm_with_fallback",
        new_callable=AsyncMock,
        side_effect=[header_response, section_response],
    ) as mock_call:
        blocks, clamped = await _plan_section(
            section, background_tasks=None, on_retry=None
        )

    assert mock_call.await_args_list[0].args[0] == build_visual_entry_header_prompt(
        "Experience"
    )
    header_atoms = sorted(
        (section.content[position] for position in header_positions),
        key=lambda atom: (
            atom.bbox[1] if atom.bbox else 0.0,
            atom.bbox[0] if atom.bbox else 0.0,
        ),
    )
    assert mock_call.await_args_list[0].args[1] == format_visual_entry_header(
        header_atoms
    )
    fields_by_atom: dict[str, list[tuple[str, tuple[float, float, float, float]]]] = {}
    for role, atoms in blocks[0].fields:
        fields_by_atom.setdefault(role, []).extend(
            (atom.text, atom.bbox) for atom in atoms
        )
    # Visual header overrides the planner's labels for atoms in the header band.
    assert ("Zalo – VNG Corporation", (40.0, 384.0, 166.0, 394.0)) in fields_by_atom[
        "o"
    ]
    assert (
        "Ho Chi Minh City, Vietnam",
        (459.0, 385.0, 572.0, 394.0),
    ) in fields_by_atom["l"]
    assert (
        "Software Engineer, Zalo PC",
        (40.0, 397.0, 152.0, 406.0),
    ) in fields_by_atom["t"]
    assert ("May 2022 – Mar 2024", (482.0, 397.0, 572.0, 406.0)) in fields_by_atom["d"]


def test_v31_tail_bullet_count_auto_absorption():
    ledger = build_source_ledger(_raw())
    # 3 content atoms: Research Assistant, Soonchunhyang University, • Built source-grounded mapper.
    section = _LedgerSection(type="experience", title=ledger[2], content=ledger[3:])

    # LLM incorrectly returns count=13 for bullets instead of 1
    plan = LLMSectionCursorPlanResponse.model_validate(
        {"b": [{"k": "e", "s": [["t", 1], ["o", 1], ["b", 13]]}]}
    )
    blocks, clamped = compile_section_cursor_plan(section, plan)
    assert len(blocks) == 1
    assert blocks[0].fields[-1][0] == "b"
    # Auto-clamped to consume remaining 1 atom
    assert len(blocks[0].fields[-1][1]) == 1
    assert blocks[0].fields[-1][1][0].text == "Built source-grounded mapper."
    assert clamped is True


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


# ---------------------------------------------------------------------------
# Identity preamble name detection (regression for vinh.pdf email-first bug)
# ---------------------------------------------------------------------------


def _ledger_atom(text: str, block_id: str = "b", index: int = 0) -> SourceLedgerAtom:
    return SourceLedgerAtom(
        index=index,
        block_id=block_id,
        text=text,
        page=1,
        reading_order=index,
        bbox=None,
        start_offset=0,
        end_offset=len(text),
    )


def test_looks_like_name_accepts_person_names_and_rejects_jargon():
    assert _looks_like_name("PHAM HONG VINH") is True
    assert _looks_like_name("Nguyen Van Duy") is True
    assert _looks_like_name("Jane Doe") is True
    assert _looks_like_name("This is way too many words for a real name") is False
    assert _looks_like_name("developer") is False
    assert _looks_like_name("Backend Developer") is False
    assert _looks_like_name("Software Engineer and Researcher") is False
    assert _looks_like_name("") is False


def test_build_identity_recovers_name_when_email_sorts_first():
    """Regression: layout sort may place email before the name line. The
    name at offset > 0 must still be captured instead of being silently
    dropped by the offset-zero heuristic (vinh.pdf failure)."""
    preamble = [
        _ledger_atom("phamvinh257@gmail.com", "b_email", 0),
        _ledger_atom("PHAM HONG VINH", "b_name", 1),
        _ledger_atom("github.com/rootonchair", "b_link1", 2),
        _ledger_atom("linkedin.com/in/phvinh2000", "b_link2", 3),
        _ledger_atom("0943463275", "b_phone", 4),
    ]

    identity, assigned = _build_identity(preamble)

    assert identity.full_name == "PHAM HONG VINH"
    assert identity.email == "phamvinh257@gmail.com"
    assert identity.phone == "0943463275"
    assert identity.links == [
        "github.com/rootonchair",
        "linkedin.com/in/phvinh2000",
    ]
    assert identity.headline is None
    assert 1 in assigned


def test_build_identity_still_treats_offset_zero_as_name_when_present():
    """Regression: name-first preamble (the common case) must keep working."""
    preamble = [
        _ledger_atom("Nguyen Van Duy", "b_name", 0),
        _ledger_atom("AI Engineer", "b_headline", 1),
        _ledger_atom("duy@example.com", "b_email", 2),
        _ledger_atom("+84 90 123 4567", "b_phone", 3),
    ]

    identity, assigned = _build_identity(preamble)

    assert identity.full_name == "Nguyen Van Duy"
    assert identity.headline == "AI Engineer"
    assert identity.email == "duy@example.com"
    assert identity.phone == "+84 90 123 4567"
    assert {0, 1, 2, 3}.issubset(assigned)


def test_build_identity_returns_none_name_when_no_name_candidate():
    """Regression: preambles without a name (only contact lines, or only
    section-heading words that look like jargon) must not be coerced into
    a fake name."""
    preamble = [
        _ledger_atom("duy@example.com", "b_email", 0),
        _ledger_atom("+84 90 123 4567", "b_phone", 1),
        _ledger_atom("Ho Chi Minh City, Vietnam", "b_loc", 2),
    ]

    identity, assigned = _build_identity(preamble)

    assert identity.full_name is None
    assert identity.headline is None
    assert identity.email == "duy@example.com"
    assert identity.phone == "+84 90 123 4567"
    assert identity.location == "Ho Chi Minh City, Vietnam"
    assert {0, 1, 2}.issubset(assigned)


def test_build_identity_does_not_treat_section_heading_words_as_name():
    """Regression: stop-word filter must keep 'Skills', 'Experience', etc.
    out of the name slot even when the layout puts them before the name."""
    preamble = [
        _ledger_atom("phamvinh257@gmail.com", "b_email", 0),
        _ledger_atom("EXPERIENCE", "b_jargon", 1),
        _ledger_atom("PHAM HONG VINH", "b_name", 2),
    ]

    identity, _assigned = _build_identity(preamble)

    assert identity.full_name == "PHAM HONG VINH"


# ---------------------------------------------------------------------------
# Skills two-column reading order (regression for vinh.pdf)
# ---------------------------------------------------------------------------


def test_vinh_skills_section_arrives_in_column_major_order():
    """Regression: a two-column skills section that the upstream reader
    would emit row-by-row (Computer Vision, English, Programming, …) must
    arrive at the cursor planner already sorted left column top-to-bottom
    then right column top-to-bottom.  No post-hoc reordering is required.
    """
    from app.models.cv_raw_extraction import (
        ExtractionMethod,
        RawBlock,
        RawExtraction,
        RawPage,
    )

    blocks = [
        RawBlock(
            block_id="b_summary",
            page=1,
            text="SUMMARY",
            extraction_method=ExtractionMethod.NATIVE_BLOCKS,
            reading_order=0,
            bbox=(40, 80, 200, 92),
        ),
        RawBlock(
            block_id="b_skills_hdr",
            page=1,
            text="SKILLS",
            extraction_method=ExtractionMethod.NATIVE_BLOCKS,
            reading_order=1,
            bbox=(40, 400, 200, 412),
        ),
        RawBlock(
            block_id="b_cv_label",
            page=1,
            text="Computer Vision",
            extraction_method=ExtractionMethod.NATIVE_BLOCKS,
            reading_order=2,
            bbox=(39, 430, 130, 442),
        ),
        RawBlock(
            block_id="b_prog_label",
            page=1,
            text="Programming",
            extraction_method=ExtractionMethod.NATIVE_BLOCKS,
            reading_order=3,
            bbox=(316, 430, 410, 442),
        ),
        RawBlock(
            block_id="b_cv_1",
            page=1,
            text="Deep models in OCR,",
            extraction_method=ExtractionMethod.NATIVE_BLOCKS,
            reading_order=4,
            bbox=(75, 448, 200, 460),
        ),
        RawBlock(
            block_id="b_prog_1",
            page=1,
            text="Pytorch, OpenCV",
            extraction_method=ExtractionMethod.NATIVE_BLOCKS,
            reading_order=5,
            bbox=(352, 448, 480, 460),
        ),
        RawBlock(
            block_id="b_cv_2",
            page=1,
            text="Object Detection,",
            extraction_method=ExtractionMethod.NATIVE_BLOCKS,
            reading_order=6,
            bbox=(75, 464, 200, 476),
        ),
        RawBlock(
            block_id="b_prog_2",
            page=1,
            text="TensorRT,",
            extraction_method=ExtractionMethod.NATIVE_BLOCKS,
            reading_order=7,
            bbox=(352, 464, 480, 476),
        ),
        RawBlock(
            block_id="b_cv_3",
            page=1,
            text="Semantic Segmentation",
            extraction_method=ExtractionMethod.NATIVE_BLOCKS,
            reading_order=8,
            bbox=(75, 480, 240, 492),
        ),
        RawBlock(
            block_id="b_prog_3",
            page=1,
            text="Triton Inference Server,",
            extraction_method=ExtractionMethod.NATIVE_BLOCKS,
            reading_order=9,
            bbox=(352, 480, 520, 492),
        ),
    ]
    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[RawPage(page=1, width=612, blocks=blocks)],
    )

    ledger = build_source_ledger(raw)

    # Find the skills section heading and verify the content atoms that
    # follow it appear in left-column-then-right-column order, with a
    # contiguous reading_order sequence.
    # NOTE (v3.3 logical blocks): comma-wrapped skill lines in the same
    # column arrive as ONE logical atom (wrap joined upstream), so each
    # column contributes label + single merged value atom with full
    # provenance in source_block_ids.
    skills_idx = next(
        index for index, atom in enumerate(ledger) if atom.text == "SKILLS"
    )
    skills_block_ids = [
        ledger[index].block_id for index in range(skills_idx + 1, len(ledger))
    ]

    assert skills_block_ids == [
        "b_cv_label",
        "b_cv_1",
        "b_prog_label",
        "b_prog_1",
    ]
    assert ledger[skills_idx + 2].source_block_ids == [
        "b_cv_1",
        "b_cv_2",
        "b_cv_3",
    ]
    assert ledger[skills_idx + 4].source_block_ids == [
        "b_prog_1",
        "b_prog_2",
        "b_prog_3",
    ]
    assert [atom.reading_order for atom in ledger] == list(range(len(ledger)))


# ---------------------------------------------------------------------------
# Logical-line joining (upstream geometry, not render text heuristics)
# ---------------------------------------------------------------------------


def _logical_block(
    block_id: str,
    text: str,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    *,
    page: int = 1,
    column_id: int | None = None,
) -> RawBlock:
    return RawBlock(
        block_id=block_id,
        page=page,
        text=text,
        bbox=(x0, y0, x1, y1),
        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
        reading_order=0,
        column_id=column_id,
    )


_PAGE_SIZES = {1: (612.0, 792.0), 2: (612.0, 792.0)}


def test_join_logical_blocks_joins_wrapped_wrap() -> None:
    prev = _logical_block(
        "p2-b35",
        "Active contributors of Transformers, a 144k stars library, with approved PRs in",
        72,
        100,
        520,
        112,
    )
    curr = _logical_block("p2-b36", "BERT and ViT models", 72, 116, 300, 128)
    merged = join_logical_blocks([prev, curr], page_sizes=_PAGE_SIZES)
    assert len(merged) == 1
    block, ids = merged[0]
    assert ids == ["p2-b35", "p2-b36"]
    assert block.text == (
        "Active contributors of Transformers, a 144k stars library, with approved PRs in"
        " BERT and ViT models"
    )
    assert block.bbox == (72, 100, 520, 128)


def test_join_logical_blocks_splits_on_title_colon() -> None:
    prev = _logical_block(
        "p1-b23",
        "eKYC OCR: Customizing model architecture for OCR modules",
        72,
        100,
        520,
        112,
    )
    curr = _logical_block(
        "p1-b30",
        "Lottery OCR: Building pipeline for extracting fields",
        72,
        116,
        520,
        128,
    )
    merged = join_logical_blocks([prev, curr], page_sizes=_PAGE_SIZES)
    assert len(merged) == 2


def test_join_logical_blocks_joins_ekyc_wrap_chain() -> None:
    lines = [
        (
            "p1-b23",
            "eKYC OCR: Customizing model architecture and training data for OCR modules",
        ),
        (
            "p1-b24",
            "in eKYC system, training CenterNet for image alignment, YOLOv5 for text",
        ),
        (
            "p1-b25",
            "detection, CRNN for text recognition, improving 20-30% accuracy across",
        ),
        ("p1-b26", "multiple fields. Annotate and fine-tuning on new data"),
        ("p1-b27", "to adapt modules for new ID document and maintaining 95% accuracy"),
    ]
    blocks = [
        _logical_block(bid, text, 72, 100 + i * 14, 520 if i < 4 else 400, 112 + i * 14)
        for i, (bid, text) in enumerate(lines)
    ]
    merged = join_logical_blocks(blocks, page_sizes=_PAGE_SIZES)
    assert len(merged) == 1
    assert merged[0][1] == [bid for bid, _ in lines]
    assert merged[0][0].text.endswith("maintaining 95% accuracy")


def test_join_logical_blocks_splits_digit_start() -> None:
    prev = _logical_block(
        "p1-b40",
        "Image Generation: Reducing image generation runtime from 2000ms to 250ms",
        72,
        100,
        520,
        112,
    )
    curr = _logical_block(
        "p1-b41",
        "87.5% decreasing by exporting TensorRT engine",
        72,
        116,
        400,
        128,
    )
    merged = join_logical_blocks([prev, curr], page_sizes=_PAGE_SIZES)
    assert len(merged) == 2


def test_join_logical_blocks_joins_publication_wrap() -> None:
    prev = _logical_block(
        "p2-b43",
        "2nd Author - Dynamic Context-Aware Streaming Pretrained Language Model For",
        72,
        781,
        547,
        795,
        page=2,
    )
    curr = _logical_block(
        "p2-b44",
        "Inverse Text Normalization (Interspeech 2025)",
        72,
        797,
        322,
        811,
        page=2,
    )
    merged = join_logical_blocks([prev, curr], page_sizes=_PAGE_SIZES)
    assert len(merged) == 1
    assert merged[0][0].text.endswith("Inverse Text Normalization (Interspeech 2025)")


def test_join_logical_blocks_never_joins_headings() -> None:
    heading = _logical_block("h1", "PUBLICATIONS", 72, 770, 150, 782, page=2)
    body = _logical_block(
        "p2-b43",
        "2nd Author - Dynamic Context-Aware Streaming Model",
        72,
        781,
        547,
        795,
        page=2,
    )
    merged = join_logical_blocks(
        [heading, body], heading_block_ids={"h1"}, page_sizes=_PAGE_SIZES
    )
    assert len(merged) == 2


def test_build_source_ledger_emits_one_atom_per_logical_bullet() -> None:
    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[
            RawPage(
                page=1,
                width=612.0,
                height=792.0,
                blocks=[
                    RawBlock(
                        block_id="p1-name",
                        page=1,
                        text="Nguyen Duy",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=0,
                    ),
                    RawBlock(
                        block_id="p1-h",
                        page=1,
                        text="PROJECTS",
                        bbox=(72, 60, 200, 72),
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=1,
                    ),
                    RawBlock(
                        block_id="p1-b1",
                        page=1,
                        text="Active contributors of Transformers, a 144k stars library, with approved PRs in",
                        bbox=(72, 100, 520, 112),
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=2,
                    ),
                    RawBlock(
                        block_id="p1-b2",
                        page=1,
                        text="BERT and ViT models",
                        bbox=(72, 116, 300, 128),
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=3,
                    ),
                ],
            )
        ],
    )
    ledger = build_source_ledger(raw)
    merged = [atom for atom in ledger if atom.text.startswith("Active contributors")]
    assert len(merged) == 1
    assert merged[0].text.endswith("BERT and ViT models")
    assert merged[0].source_block_ids == ["p1-b1", "p1-b2"]


def test_compile_section_cursor_plan_clamps_scalar_overrun() -> None:
    """An overshooting plan (LLM miscount) clamps to available atoms with a
    flag instead of killing the whole section: partial content beats total
    loss, and the caller records a loud mismatch warning."""
    from app.models.cv_range_plan import SourceLedgerAtom

    heading = SourceLedgerAtom(
        index=0,
        block_id="h",
        text="PROJECTS",
        page=1,
        reading_order=0,
        start_offset=0,
        end_offset=8,
    )
    only = SourceLedgerAtom(
        index=1,
        block_id="b1",
        text="Single logical bullet",
        page=1,
        reading_order=1,
        start_offset=0,
        end_offset=21,
    )
    section = _LedgerSection(type="projects", title=heading, content=[only])
    plan = LLMSectionCursorPlanResponse.model_validate(
        {"b": [{"k": "e", "s": [["t", 1], ["b", 1]]}]}
    )
    blocks, clamped = compile_section_cursor_plan(section, plan)
    assert clamped is True
    assert len(blocks) == 1
    rendered = _render_block(blocks[0], block_id="test-clamp")
    assert rendered.title == "Single logical bullet"
    assert rendered.bullets == []


def test_render_block_keeps_logical_atoms_separate() -> None:
    from app.models.cv_range_plan import SourceLedgerAtom

    def atom(i: int, text: str) -> SourceLedgerAtom:
        return SourceLedgerAtom(
            index=i,
            block_id=f"b{i}",
            text=text,
            page=1,
            reading_order=i,
            start_offset=0,
            end_offset=len(text),
        )

    block = _ResolvedBlock(
        kind="e",
        fields=[
            ("t", [atom(0, "Project X")]),
            ("b", [atom(1, "First bullet"), atom(2, "Second bullet")]),
        ],
    )
    rendered = _render_block(block, block_id="test-logical")
    assert rendered.bullets == ["First bullet", "Second bullet"]


def test_build_identity_merges_multiline_name() -> None:
    """First/last name on separate PDF lines merge into one full_name with
    provenance for both blocks; the following headline stays separate."""
    from app.models.cv_range_plan import SourceLedgerAtom

    def atom(i: int, text: str) -> SourceLedgerAtom:
        return SourceLedgerAtom(
            index=i,
            block_id=f"p{i}",
            text=text,
            page=1,
            reading_order=i,
            start_offset=0,
            end_offset=len(text),
        )

    preamble = [
        atom(0, "Trung"),
        atom(1, "Dao"),
        atom(2, "tdao6@wisc.edu"),
    ]
    identity, assigned = _build_identity(preamble)
    assert identity.full_name == "Trung Dao"
    assert identity.field_source_block_ids.full_name == ["p0", "p1"]
    assert identity.email == "tdao6@wisc.edu"
    assert assigned == {0, 1, 2}


def test_build_identity_does_not_merge_headline_into_name() -> None:
    """A headline after a single-line name must not merge into the name."""
    from app.models.cv_range_plan import SourceLedgerAtom

    def atom(i: int, text: str) -> SourceLedgerAtom:
        return SourceLedgerAtom(
            index=i,
            block_id=f"p{i}",
            text=text,
            page=1,
            reading_order=i,
            start_offset=0,
            end_offset=len(text),
        )

    preamble = [atom(0, "Nguyen Duy"), atom(1, "AI Engineer")]
    identity, _ = _build_identity(preamble)
    assert identity.full_name == "Nguyen Duy"
    assert identity.headline == "AI Engineer"


def test_references_heading_is_own_section() -> None:
    """A References block starts its own section so referee lines never
    merge into a neighboring skills line or get planned as skills."""
    from app.services.section_vocabulary import classify_heading

    assert classify_heading("References") is not None
    assert classify_heading("References")[0] == "custom"


def test_looks_like_name_rejects_email_and_job_title() -> None:
    from app.services.cv_range_plan_service import _looks_like_name

    assert _looks_like_name("phamvinh257@gmail.com") is False
    assert _looks_like_name("Senior AI Engineer") is False
    assert _looks_like_name("AI Researcher") is False
    assert _looks_like_name("PHAM HONG VINH") is True
    assert _looks_like_name("TRẦN VĂN AN") is True


def test_build_identity_swaps_email_and_name_candidate() -> None:
    from app.models.cv_range_plan import SourceLedgerAtom
    from app.services.cv_range_plan_service import _build_identity

    def atom(i: int, text: str) -> SourceLedgerAtom:
        return SourceLedgerAtom(
            index=i,
            block_id=f"p{i}",
            text=text,
            page=1,
            reading_order=i,
            start_offset=0,
            end_offset=len(text),
        )

    preamble = [
        atom(0, "phamvinh257@gmail.com"),
        atom(1, "PHAM HONG VINH"),
        atom(2, "Senior AI Engineer"),
        atom(
            3,
            "https://www.google.com/url?q=https://linkedin.com/in/phvinh2000&sa=D&usg=XYZ",
        ),
    ]
    identity, assigned = _build_identity(preamble)
    assert identity.full_name == "PHAM HONG VINH"
    assert identity.email == "phamvinh257@gmail.com"
    assert identity.headline == "Senior AI Engineer"
    assert identity.links == ["https://linkedin.com/in/phvinh2000"]
