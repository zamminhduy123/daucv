"""Adversarial and functional test suite for Phase 5 evidence-constrained CV rewriting."""

from uuid import uuid4

import pytest

from app.models.cv_document_v2 import (
    ContentOrigin,
    CVDocumentV2,
    CVEntryBlock,
    CVIdentity,
    CVParagraphBlock,
    CVReconstructionDiagnostics,
    CVRewriteOperation,
    CVSection,
    CVSkillGroupBlock,
    CVSourceCoverageDiagnostics,
    CVTailoringDiagnostics,
)
from app.models.cv_raw_extraction import RawBlock, RawExtraction, RawPage
from app.services.cv_rewrite_service import (
    build_evidence_bundle,
    extract_protected_facts,
    rewrite_cv,
)
from app.services.cv_tailoring_service import (
    validate_block_rewrite_deterministic,
    validate_tailored_document_gate,
    verify_block_rewrite_semantics,
)
from app.services.tailored_cv_metadata import (
    issue_tailoring_entitlement_v3,
    verify_tailoring_entitlement_v3,
)


@pytest.fixture
def sample_raw_extraction() -> RawExtraction:
    return RawExtraction(
        extraction_version="1.0.0",
        method="native_blocks",
        pages=[
            RawPage(
                page=1,
                blocks=[
                    RawBlock(
                        block_id="b1",
                        page=1,
                        text="Software Engineer at Acme Corp from 2020 to 2022. Assisted team with 5 Python microservices.",
                        extraction_method="native_blocks",
                    ),
                    RawBlock(
                        block_id="b2",
                        page=1,
                        text="Summary: Experienced developer with Python and FastAPI skills.",
                        extraction_method="native_blocks",
                    ),
                    RawBlock(
                        block_id="b3",
                        page=1,
                        text="Skills: Python, FastAPI, Docker, PostgreSQL",
                        extraction_method="native_blocks",
                    ),
                ],
            )
        ],
    )


@pytest.fixture
def sample_source_document() -> CVDocumentV2:
    return CVDocumentV2(
        schema_version=2,
        extraction_version="1.0.0",
        parser_version="1.0.0",
        reconstruction_version=4,
        requires_reprocessing=False,
        identity=CVIdentity(full_name="John Doe", email="john@example.com"),
        summary=CVParagraphBlock(
            block_id="b2",
            text="Experienced developer with Python and FastAPI skills.",
            source_block_ids=["b2"],
            origin=ContentOrigin.EXTRACTED,
        ),
        sections=[
            CVSection(
                type="experience",
                title="Experience",
                source_block_ids=["b1"],
                blocks=[
                    CVEntryBlock(
                        block_id="b1",
                        title="Software Engineer",
                        organization="Acme Corp",
                        date="2020 - 2022",
                        bullets=["Assisted team with 5 Python microservices."],
                        source_block_ids=["b1"],
                        origin=ContentOrigin.EXTRACTED,
                    )
                ],
            ),
            CVSection(
                type="skills",
                title="Skills",
                source_block_ids=["b3"],
                blocks=[
                    CVSkillGroupBlock(
                        block_id="b3",
                        label="Backend",
                        skills=["Python", "FastAPI", "Docker", "PostgreSQL"],
                        source_block_ids=["b3"],
                        origin=ContentOrigin.EXTRACTED,
                    )
                ],
            ),
        ],
        reconstruction_diagnostics=CVReconstructionDiagnostics(
            reconstruction_version=4,
            warnings=[],
            block_confidence={"b1": 1.0, "b2": 1.0, "b3": 1.0},
            source_coverage=CVSourceCoverageDiagnostics(
                raw_block_count=3,
                accounted_block_count=3,
                significant_character_count=150,
                mapped_character_count=150,
                coverage_ratio=1.0,
            ),
        ),
    )


def test_extract_protected_facts():
    text = "Managed 5 Python microservices with 99.9% uptime in 2022."
    facts = extract_protected_facts(text)
    assert "5" in facts
    assert "99.9%" in facts
    assert "2022" in facts
    assert "python" in facts


def test_build_evidence_bundle(sample_source_document, sample_raw_extraction):
    block = sample_source_document.sections[0].blocks[0]
    bundle = build_evidence_bundle(
        sample_source_document, sample_raw_extraction, block, "bullets", "en"
    )
    assert bundle is not None
    assert bundle.block_id == "b1"
    assert bundle.field == "bullets"
    assert "5" in bundle.protected_facts
    assert "2020" in bundle.protected_facts


def test_invented_metric_rejected(sample_source_document, sample_raw_extraction):
    block = sample_source_document.sections[0].blocks[0]
    bundle = build_evidence_bundle(
        sample_source_document, sample_raw_extraction, block, "bullets", "en"
    )
    op = CVRewriteOperation(
        block_id="b1",
        field="bullets",
        original_value_hash=bundle.original_value_hash,
        proposed_value=["Assisted team with 50 Python microservices."],
    )
    ok, reasons = validate_block_rewrite_deterministic(bundle, op)
    assert not ok
    assert "unsupported_number_invented" in reasons


def test_existing_metric_removal_allowed(sample_source_document, sample_raw_extraction):
    """Number removal is now permitted by the deterministic gate (downgraded from fatal)."""
    block = sample_source_document.sections[0].blocks[0]
    bundle = build_evidence_bundle(
        sample_source_document, sample_raw_extraction, block, "bullets", "en"
    )
    op = CVRewriteOperation(
        block_id="b1",
        field="bullets",
        original_value_hash=bundle.original_value_hash,
        proposed_value=["Assisted team with Python microservices."],
    )
    ok, reasons = validate_block_rewrite_deterministic(bundle, op)
    # existing_number_removed no longer triggers a gate failure
    assert "existing_number_removed" not in reasons


def test_responsibility_inflation_assisted_to_led_rejected(
    sample_source_document, sample_raw_extraction
):
    block = sample_source_document.sections[0].blocks[0]
    bundle = build_evidence_bundle(
        sample_source_document, sample_raw_extraction, block, "bullets", "en"
    )
    op = CVRewriteOperation(
        block_id="b1",
        field="bullets",
        original_value_hash=bundle.original_value_hash,
        proposed_value=["Led team with 5 Python microservices."],
    )
    ok, reasons = verify_block_rewrite_semantics(bundle, op)
    assert not ok
    assert "responsibility_inflation_detected" in reasons


def test_unsupported_buzzword_rejected(sample_source_document, sample_raw_extraction):
    block = sample_source_document.sections[0].blocks[0]
    bundle = build_evidence_bundle(
        sample_source_document, sample_raw_extraction, block, "bullets", "en"
    )
    op = CVRewriteOperation(
        block_id="b1",
        field="bullets",
        original_value_hash=bundle.original_value_hash,
        proposed_value=[
            "Assisted team with 5 scalable high-performing Python microservices."
        ],
    )
    ok, reasons = validate_block_rewrite_deterministic(bundle, op)
    assert not ok
    assert any("unsupported_buzzword" in r for r in reasons)


def test_placeholder_output_rejected(sample_source_document, sample_raw_extraction):
    block = sample_source_document.sections[0].blocks[0]
    bundle = build_evidence_bundle(
        sample_source_document, sample_raw_extraction, block, "bullets", "en"
    )
    op = CVRewriteOperation(
        block_id="b1",
        field="bullets",
        original_value_hash=bundle.original_value_hash,
        proposed_value=["Assisted team with [N users] Python microservices."],
    )
    ok, reasons = validate_block_rewrite_deterministic(bundle, op)
    assert not ok
    assert "placeholder_detected" in reasons


def test_bullet_count_changes_rejected(sample_source_document, sample_raw_extraction):
    block = sample_source_document.sections[0].blocks[0]
    bundle = build_evidence_bundle(
        sample_source_document, sample_raw_extraction, block, "bullets", "en"
    )
    op = CVRewriteOperation(
        block_id="b1",
        field="bullets",
        original_value_hash=bundle.original_value_hash,
        proposed_value=["Assisted team with 5 microservices.", "Added second bullet."],
    )
    ok, reasons = validate_block_rewrite_deterministic(bundle, op)
    assert not ok
    assert "bullet_count_changed" in reasons


def test_skill_additions_or_removals_rejected(
    sample_source_document, sample_raw_extraction
):
    block = sample_source_document.sections[1].blocks[0]
    bundle = build_evidence_bundle(
        sample_source_document, sample_raw_extraction, block, "skills", "en"
    )

    # Adding Kubernetes
    op_add = CVRewriteOperation(
        block_id="b3",
        field="skills",
        original_value_hash=bundle.original_value_hash,
        proposed_value=["Python", "FastAPI", "Docker", "PostgreSQL", "Kubernetes"],
    )
    ok, reasons = validate_block_rewrite_deterministic(bundle, op_add)
    assert not ok
    assert "skills_added_or_removed" in reasons

    # Valid reordering allowed
    op_reorder = CVRewriteOperation(
        block_id="b3",
        field="skills",
        original_value_hash=bundle.original_value_hash,
        proposed_value=["FastAPI", "Python", "PostgreSQL", "Docker"],
    )
    ok_r, _reasons_r = validate_block_rewrite_deterministic(bundle, op_reorder)
    assert ok_r


def test_stale_original_value_hash_rejected(
    sample_source_document, sample_raw_extraction
):
    block = sample_source_document.sections[0].blocks[0]
    bundle = build_evidence_bundle(
        sample_source_document, sample_raw_extraction, block, "bullets", "en"
    )
    op = CVRewriteOperation(
        block_id="b1",
        field="bullets",
        original_value_hash="wrong_hash_12345678",
        proposed_value=["Assisted team with 5 Python microservices."],
    )
    ok, reasons = validate_block_rewrite_deterministic(bundle, op)
    assert not ok
    assert "stale_original_value_hash" in reasons


@pytest.mark.asyncio
async def test_rewrite_cv_fallback_preserves_source(
    sample_source_document, sample_raw_extraction, monkeypatch
):
    """Provider failure or timeout preserves source document with fallback flags."""
    from fastapi import HTTPException

    async def mock_call_llm(*args, **kwargs):
        raise HTTPException(status_code=502, detail="LLM Timeout or Provider Error")

    monkeypatch.setattr(
        "app.services.cv_rewrite_service.call_llm_with_fallback", mock_call_llm
    )

    result = await rewrite_cv(
        source_document=sample_source_document,
        source_raw_extraction=sample_raw_extraction,
        jd_text="Looking for a Python developer",
        source_language="en",
    )

    assert result.diagnostics.used_fallback is True
    assert result.diagnostics.accepted_count == 0
    assert result.diagnostics.preserved_count > 0
    assert result.tailored_document == sample_source_document


def test_tailored_document_gate_fails_on_tampered_identity(sample_source_document):
    from app.services.tailored_cv_metadata import canonical_source_document_hash

    tailored = sample_source_document.model_copy(deep=True)
    tailored.identity.full_name = "Hacker Name"
    src_hash = canonical_source_document_hash(sample_source_document)
    diag = CVTailoringDiagnostics(source_document_hash=src_hash, jd_hash="b")
    with pytest.raises(ValueError, match="document metadata or identity changed"):
        validate_tailored_document_gate(sample_source_document, tailored, diag)


def test_v3_entitlement_issuance_and_verification(sample_source_document):
    import hashlib

    from app.services.tailored_cv_metadata import canonical_source_document_hash

    user_id = uuid4()
    tailored = sample_source_document.model_copy(deep=True)
    src_hash = canonical_source_document_hash(sample_source_document)
    jd_hash = hashlib.sha256(b"jd_text").hexdigest()
    diag = CVTailoringDiagnostics(source_document_hash=src_hash, jd_hash=jd_hash)

    entitlement = issue_tailoring_entitlement_v3(
        user_id,
        "source_text",
        "jd_text",
        sample_source_document,
        tailored,
        diag,
    )
    assert entitlement.startswith("v3.")

    key = verify_tailoring_entitlement_v3(
        entitlement,
        user_id,
        "source_text",
        "jd_text",
        sample_source_document,
        tailored,
        diag,
    )
    assert len(key) == 32
