from app.models.cv_document_v2 import (
    CVBlockRewrite,
    CVDocumentV2,
    CVEntryBlock,
    CVIdentity,
    CVParagraphBlock,
    CVSection,
    CVSkillGroupBlock,
)
from app.services.cv_tailoring_service import (
    apply_block_rewrites,
    rewrite_payload,
    validate_tailored_document,
)


def _document() -> CVDocumentV2:
    return CVDocumentV2(
        identity=CVIdentity(name="Duy", headline="Backend Engineer"),
        summary=CVParagraphBlock(block_id="summary-1", text="Backend engineer."),
        sections=[
            CVSection(
                id="experience",
                type="experience",
                title="Experience",
                blocks=[
                    CVEntryBlock(
                        block_id="entry-1",
                        title="Engineer",
                        organization="TechCorp",
                        date="2023",
                        bullets=["Built Python APIs."],
                    ),
                ],
            ),
            CVSection(
                id="skills",
                type="skills",
                title="Skills",
                blocks=[
                    CVSkillGroupBlock(
                        block_id="skills-1",
                        label="Backend",
                        skills=["Python", "FastAPI"],
                    ),
                ],
            ),
        ],
    )


def test_rewrite_payload_uses_ids_and_only_mutable_fields() -> None:
    payload = rewrite_payload(_document())

    assert '"block_id": "entry-1"' in payload
    assert '"original_bullets": ["Built Python APIs."]' in payload
    assert "TechCorp" not in payload


def test_safe_rewrites_preserve_structure_and_original_values() -> None:
    document = _document()
    rewritten, warnings = apply_block_rewrites(
        document,
        [
            CVBlockRewrite(block_id="summary-1", text="Backend Python engineer."),
            CVBlockRewrite(block_id="entry-1", bullets=["Clearly built Python APIs."]),
            CVBlockRewrite(block_id="skills-1", skills=["FastAPI", "Python"]),
        ],
        "Backend engineer. Built Python APIs. Python FastAPI",
    )

    assert warnings == []
    assert rewritten.identity == document.identity
    assert len(rewritten.sections) == len(document.sections)
    entry = rewritten.sections[0].blocks[0]
    assert entry.organization == "TechCorp"
    assert entry.date == "2023"
    assert entry.original_values["bullets"] == ["Built Python APIs."]
    assert entry.tailored_values["bullets"] == ["Clearly built Python APIs."]


def test_unsupported_claim_rejects_only_affected_block() -> None:
    document = _document()
    rewritten, warnings = apply_block_rewrites(
        document,
        [
            CVBlockRewrite(block_id="summary-1", text="Backend engineer."),
            CVBlockRewrite(
                block_id="entry-1",
                bullets=["Improved Kubernetes throughput by 40%."],
            ),
            CVBlockRewrite(block_id="skills-1", skills=["Python", "FastAPI"]),
        ],
        "Backend engineer. Built Python APIs. Python FastAPI",
    )

    entry = rewritten.sections[0].blocks[0]
    assert entry.bullets == ["Built Python APIs."]
    assert any("entry-1:unsupported_number" in warning for warning in warnings)
    assert any("entry-1" in warning for warning in rewritten.reconstruction_warnings)


def test_unsupported_named_entity_is_rejected() -> None:
    document = _document()
    rewritten, warnings = apply_block_rewrites(
        document,
        [
            CVBlockRewrite(
                block_id="summary-1",
                text="Backend engineer delivering systems at Google.",
            ),
            CVBlockRewrite(block_id="entry-1", bullets=["Built Python APIs."]),
            CVBlockRewrite(block_id="skills-1", skills=["Python", "FastAPI"]),
        ],
        "Backend engineer. Built Python APIs. Python FastAPI",
    )

    assert rewritten.summary is not None
    assert rewritten.summary.text == "Backend engineer."
    assert "rewrite_rejected:summary-1:unsupported_named_entity" in warnings


def test_unsupported_prose_claim_is_rejected() -> None:
    document = _document()
    rewritten, warnings = apply_block_rewrites(
        document,
        [
            CVBlockRewrite(block_id="summary-1", preserve=True),
            CVBlockRewrite(
                block_id="entry-1",
                bullets=["Led enterprise strategy worldwide."],
            ),
            CVBlockRewrite(block_id="skills-1", preserve=True),
        ],
        "Backend engineer. Built Python APIs. Python FastAPI",
    )

    assert rewritten.sections[0].blocks[0].bullets == ["Built Python APIs."]
    assert "rewrite_rejected:entry-1:unsupported_claim_terms" in warnings


def test_claim_bearing_allowlist_words_cannot_create_new_claims() -> None:
    document = _document()
    document.sections[0].blocks[0].bullets = ["Worked on backend API."]

    rewritten, warnings = apply_block_rewrites(
        document,
        [
            CVBlockRewrite(block_id="summary-1", preserve=True),
            CVBlockRewrite(
                block_id="entry-1",
                bullets=["Improved reliable backend API."],
            ),
            CVBlockRewrite(block_id="skills-1", preserve=True),
        ],
        "Backend engineer. Worked on backend API. Python FastAPI",
    )

    assert rewritten.sections[0].blocks[0].bullets == ["Worked on backend API."]
    assert "rewrite_rejected:entry-1:unsupported_claim_terms" in warnings


def test_persisted_candidate_rejects_structure_and_immutable_mutations() -> None:
    source = _document()
    candidate = source.model_copy(deep=True)
    candidate.identity.name = "Someone Else"
    candidate.sections[0].blocks[0].organization = "Other Corp"
    candidate.sections[0].blocks[0].bullets = ["Built reliable Python APIs."]

    validated, warnings = validate_tailored_document(
        source,
        candidate,
        "Backend engineer. Built Python APIs. Python FastAPI",
    )

    assert validated.identity.name == "Duy"
    assert validated.sections[0].blocks[0].organization == "TechCorp"
    assert validated.sections[0].blocks[0].bullets == ["Built Python APIs."]
    assert "rewrite_structure_rejected:identity_changed" in warnings
    assert any("immutable_fields_changed" in warning for warning in warnings)


def test_missing_and_unknown_ids_are_observable_without_structure_changes() -> None:
    document = _document()
    rewritten, warnings = apply_block_rewrites(
        document,
        [CVBlockRewrite(block_id="not-real", text="Changed")],
        "Backend engineer. Built Python APIs. Python FastAPI",
    )

    assert rewritten == document.model_copy(
        update={"reconstruction_warnings": rewritten.reconstruction_warnings},
    )
    assert any(warning.startswith("rewrite_missing:") for warning in warnings)
    assert "rewrite_rejected:not-real:unknown_block_id" in warnings


def test_immutable_block_can_be_returned_as_explicitly_preserved() -> None:
    document = _document()
    rewrites = [
        CVBlockRewrite(block_id="summary-1", preserve=True),
        CVBlockRewrite(block_id="entry-1", preserve=True),
        CVBlockRewrite(block_id="skills-1", preserve=True),
    ]

    rewritten, warnings = apply_block_rewrites(
        document,
        rewrites,
        "Backend engineer. Built Python APIs. Python FastAPI",
    )

    assert rewritten == document
    assert warnings == []
