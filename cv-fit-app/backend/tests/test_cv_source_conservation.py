from app.models.cv_document_v2 import (
    CVDocumentV2,
    CVEntryBlock,
    CVIdentity,
    CVIdentitySourceMap,
    CVParagraphBlock,
    CVSection,
    LLMUnmappedReference,
)
from app.models.cv_raw_extraction import (
    ExtractionMethod,
    RawBlock,
    RawExtraction,
    RawPage,
)
from app.services.cv_provenance_service import audit_source_conservation
from app.services.cv_reconstruction_service import validate_reconstruction_gate


def _raw(blocks_data: list[tuple[str, str]]) -> RawExtraction:
    blocks = [
        RawBlock(
            block_id=bid,
            page=1,
            text=txt,
            extraction_method=ExtractionMethod.NATIVE_BLOCKS,
            reading_order=i,
        )
        for i, (bid, txt) in enumerate(blocks_data)
    ]
    return RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS, pages=[RawPage(page=1, blocks=blocks)]
    )


def _doc() -> CVDocumentV2:
    return CVDocumentV2(raw_extraction_id="dummy", identity=CVIdentity(), sections=[])


def test_partially_used_raw_block_detects_substantive_residual():
    raw = _raw(
        [
            (
                "b1",
                "Work Experience\nSenior Software Engineer at Acme Corp 2020-2023. Built payment systems.",
            )
        ]
    )
    doc = _doc()
    doc.sections = [
        CVSection(
            title="Work Experience",
            type="experience",
            source_block_ids=["b1"],
            blocks=[
                CVEntryBlock(
                    block_id="e1",
                    title="Senior Software Engineer",
                    source_block_ids=["b1"],
                )
            ],
        )
    ]
    res = audit_source_conservation(raw, doc)
    assert not res.is_valid
    assert any(
        issue.code == "substantive_source_omission" for issue in res.diagnostics.issues
    )
    assert res.diagnostics.substantive_unmapped_character_count > 0


def test_combined_contact_row_grounding():
    raw = _raw(
        [("b1", "John Doe | john@example.com | 123-456-7890 | San Francisco, CA")]
    )
    doc = _doc()
    doc.identity = CVIdentity(
        full_name="John Doe",
        email="john@example.com",
        phone="123-456-7890",
        location="San Francisco, CA",
        field_source_block_ids=CVIdentitySourceMap(
            full_name=["b1"], email=["b1"], phone=["b1"], location=["b1"]
        ),
    )
    res = audit_source_conservation(raw, doc)
    assert res.is_valid
    assert not any(
        issue.code == "duplicate_semantic_ownership" for issue in res.diagnostics.issues
    )


def test_single_entry_row_grounding():
    raw = _raw(
        [
            (
                "b1",
                "Work\nSoftware Engineer | Acme | NY | 2020-2022 | Built scaling architecture",
            )
        ]
    )
    doc = _doc()
    doc.sections = [
        CVSection(
            title="Work",
            type="experience",
            source_block_ids=["b1"],
            blocks=[
                CVEntryBlock(
                    block_id="e1",
                    title="Software Engineer",
                    organization="Acme",
                    location="NY",
                    date="2020-2022",
                    bullets=["Built scaling architecture"],
                    source_block_ids=["b1"],
                )
            ],
        )
    ]
    res = audit_source_conservation(raw, doc)
    assert res.is_valid


def test_section_heading_and_nested_blocks_hierarchical_parent():
    raw = _raw([("b1", "Work Experience\nSoftware Engineer")])
    doc = _doc()
    doc.sections = [
        CVSection(
            title="Work Experience",
            type="experience",
            source_block_ids=["b1"],
            blocks=[
                CVEntryBlock(
                    block_id="e1", title="Software Engineer", source_block_ids=["b1"]
                )
            ],
        )
    ]
    res = audit_source_conservation(raw, doc)
    assert res.is_valid
    assert not any(
        issue.code == "duplicate_semantic_ownership" for issue in res.diagnostics.issues
    )


def test_two_sibling_blocks_same_source_duplicate_ownership():
    raw = _raw([("b1", "Work\nSoftware Engineer")])
    doc = _doc()
    doc.sections = [
        CVSection(
            title="Work",
            type="experience",
            source_block_ids=["b1"],
            blocks=[
                CVEntryBlock(
                    block_id="e1", title="Software Engineer", source_block_ids=["b1"]
                ),
                CVEntryBlock(
                    block_id="e2", title="Software Engineer", source_block_ids=["b1"]
                ),
            ],
        )
    ]
    res = audit_source_conservation(raw, doc)
    assert not res.is_valid
    assert any(
        issue.code in {"duplicate_semantic_ownership", "unmatched_semantic_leaf"}
        for issue in res.diagnostics.issues
    )


def test_two_identical_occurrences_matched_distinctly():
    raw = _raw([("b1", "Skills\nPython, Python")])
    doc = _doc()
    doc.sections = [
        CVSection(
            title="Skills",
            type="skills",
            source_block_ids=["b1"],
            blocks=[
                CVEntryBlock(block_id="e1", title="Python", source_block_ids=["b1"]),
                CVEntryBlock(block_id="e2", title="Python", source_block_ids=["b1"]),
            ],
        )
    ]
    res = audit_source_conservation(raw, doc)
    assert res.is_valid


def test_valid_block_id_with_wrong_text_fails():
    raw = _raw([("b1", "Work\nJava Developer")])
    doc = _doc()
    doc.sections = [
        CVSection(
            title="Work",
            type="experience",
            source_block_ids=["b1"],
            blocks=[
                CVEntryBlock(
                    block_id="e1", title="Python Developer", source_block_ids=["b1"]
                )
            ],
        )
    ]
    res = audit_source_conservation(raw, doc)
    assert not res.is_valid
    assert any(
        issue.code in {"substantive_source_omission", "unmatched_semantic_leaf"}
        for issue in res.diagnostics.issues
    )


def test_unknown_source_block_ids_raises_or_reports():
    raw = _raw([("b1", "Work\nDev")])
    doc = _doc()
    doc.sections = [
        CVSection(
            title="Work",
            type="experience",
            source_block_ids=["b1"],
            blocks=[
                CVEntryBlock(
                    block_id="e1", title="Dev", source_block_ids=["nonexistent_id"]
                )
            ],
        )
    ]
    res = audit_source_conservation(raw, doc)
    assert not res.is_valid
    assert any(
        issue.code in {"unknown_source_reference", "unmatched_semantic_leaf"}
        for issue in res.diagnostics.issues
    )


def test_multi_block_summary_conservation():
    raw = _raw([("b1", "I am a"), ("b2", "developer")])
    doc = _doc()
    doc.summary = CVParagraphBlock(
        text="I am a developer", source_block_ids=["b1", "b2"]
    )
    res = audit_source_conservation(raw, doc)
    assert res.is_valid


def test_section_reordering_conservation():
    raw = _raw([("b1", "Skills\nPython"), ("b2", "Work\nDev")])
    doc = _doc()
    doc.sections = [
        CVSection(
            title="Work",
            type="experience",
            source_block_ids=["b2"],
            blocks=[CVParagraphBlock(text="Dev", source_block_ids=["b2"])],
        ),
        CVSection(
            title="Skills",
            type="skills",
            source_block_ids=["b1"],
            blocks=[CVParagraphBlock(text="Python", source_block_ids=["b1"])],
        ),
    ]
    res = audit_source_conservation(raw, doc)
    assert res.is_valid


def test_unicode_nfkc_normalization():
    raw = _raw([("b1", "Re\u0301sume\u0301")])
    doc = _doc()
    doc.summary = CVParagraphBlock(text="Résumé", source_block_ids=["b1"])
    res = audit_source_conservation(raw, doc)
    assert res.is_valid


def test_bullet_and_separator_benign_residual():
    raw = _raw([("b1", "Work\n• Software Engineer | Acme Corp")])
    doc = _doc()
    doc.sections = [
        CVSection(
            title="Work",
            type="experience",
            source_block_ids=["b1"],
            blocks=[
                CVEntryBlock(
                    block_id="e1",
                    title="Software Engineer",
                    organization="Acme Corp",
                    source_block_ids=["b1"],
                )
            ],
        )
    ]
    res = audit_source_conservation(raw, doc)
    assert res.is_valid


def test_metrics_and_numbers_are_substantive():
    raw = _raw([("b1", "Work\nIncreased revenue by 50%")])
    doc = _doc()
    doc.sections = [
        CVSection(
            title="Work",
            type="experience",
            source_block_ids=["b1"],
            blocks=[
                CVParagraphBlock(text="Increased revenue by", source_block_ids=["b1"])
            ],
        )
    ]
    res = audit_source_conservation(raw, doc)
    assert not res.is_valid
    assert any(
        issue.code == "substantive_source_omission" for issue in res.diagnostics.issues
    )


def test_server_generated_unmapped_fragment():
    raw = _raw([("b1", "Work\nSoftware Engineer. Extra details")])
    doc = _doc()
    doc.sections = [
        CVSection(
            title="Work",
            type="experience",
            source_block_ids=["b1"],
            blocks=[
                CVEntryBlock(
                    block_id="e1", title="Software Engineer.", source_block_ids=["b1"]
                )
            ],
        )
    ]
    res = audit_source_conservation(raw, doc)
    assert len(res.document.unmapped_content) > 0
    fragment = res.document.unmapped_content[0]
    assert fragment.block_id == "b1"
    assert fragment.reason == "parser_omission"
    assert "Extra details" in fragment.text


def test_privacy_safe_logging_and_exceptions():
    raw = _raw([("b1", "John Doe secret info")])
    doc = _doc()
    doc.identity = CVIdentity(
        full_name="John Doe",
        field_source_block_ids=CVIdentitySourceMap(full_name=["b1"]),
    )
    res = audit_source_conservation(raw, doc)
    assert not res.is_valid

    # Assert no candidate text in reasons
    for reason in res.rejection_reasons:
        assert "John Doe" not in reason
        assert "secret info" not in reason

    for issue in res.diagnostics.issues:
        assert "John Doe" not in str(issue.model_dump())
        assert "secret info" not in str(issue.model_dump())


def test_exact_ordered_multi_block_matching_fails_on_reordering():
    raw = _raw([("b1", "First Part"), ("b2", "Second Part")])
    doc = _doc()
    doc.summary = CVParagraphBlock(
        text="Second Part First Part", source_block_ids=["b1", "b2"]
    )
    res = audit_source_conservation(raw, doc)
    assert not res.is_valid
    assert any(
        issue.code == "unmatched_semantic_leaf" for issue in res.diagnostics.issues
    )


def test_exact_ordered_multi_block_matching_fails_on_invented_metrics():
    raw = _raw([("b1", "Achieved growth"), ("b2", "in Q4")])
    doc = _doc()
    doc.summary = CVParagraphBlock(
        text="Achieved 80% growth in Q4", source_block_ids=["b1", "b2"]
    )
    res = audit_source_conservation(raw, doc)
    assert not res.is_valid
    assert any(
        issue.code == "unmatched_semantic_leaf" for issue in res.diagnostics.issues
    )


def test_decomposed_unicode_preserves_exact_source_offsets():
    raw = _raw([("b1", "Re\u0301sume\u0301 Extra")])
    doc = _doc()
    doc.summary = CVParagraphBlock(text="Résumé", source_block_ids=["b1"])
    res = audit_source_conservation(raw, doc)
    assert len(res.document.unmapped_content) == 1
    unmapped = res.document.unmapped_content[0]
    assert unmapped.text == " Extra"
    assert unmapped.source_start == 8
    assert unmapped.source_end == 14


def test_unmapped_substantive_achievement_marked_decorative_fails_gate():
    raw = _raw([("b1", "Work\nBuilt payment APIs for 12 markets")])
    doc = _doc()
    doc.sections = [CVSection(title="Work", type="experience", source_block_ids=["b1"])]
    llm_unmapped = [
        LLMUnmappedReference(block_id="b1", reason="decorative_content", confidence=0.9)
    ]
    res = audit_source_conservation(raw, doc, llm_unmapped=llm_unmapped)
    assert not res.is_valid
    assert any(
        issue.code == "substantive_source_omission" for issue in res.diagnostics.issues
    )


def test_gate_allows_document_with_substantive_omission_diagnostics_as_warning():
    """The gate now warns rather than raises when substantive content is unmapped."""
    doc = _doc()
    doc.reconstruction_warnings = []
    raw = _raw([("b1", "Work\nBuilt payment APIs for 12 markets")])
    doc.sections = [CVSection(title="Work", type="experience", source_block_ids=["b1"])]
    res = audit_source_conservation(raw, doc)
    # Should NOT raise \u2014 gate now logs warnings and allows pipeline to proceed
    validate_reconstruction_gate(res.document)


def test_deterministic_fragment_ids():
    raw = _raw([("b1", "Work\nSoftware Engineer. Extra details")])
    doc = _doc()
    doc.sections = [
        CVSection(
            title="Work",
            type="experience",
            source_block_ids=["b1"],
            blocks=[
                CVEntryBlock(
                    block_id="e1", title="Software Engineer.", source_block_ids=["b1"]
                )
            ],
        )
    ]
    res1 = audit_source_conservation(raw, doc.model_copy(deep=True))
    res2 = audit_source_conservation(raw, doc.model_copy(deep=True))
    frag1 = res1.document.unmapped_content[0].fragment_id
    frag2 = res2.document.unmapped_content[0].fragment_id
    assert frag1 == frag2
