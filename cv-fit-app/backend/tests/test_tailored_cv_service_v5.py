"""Phase 5 tailored CV service integration and entitlement tests."""

from uuid import uuid4

import pytest

from app.models.cv_document_v2 import (
    ContentOrigin,
    CVDocumentV2,
    CVIdentity,
    CVParagraphBlock,
    CVReconstructionDiagnostics,
    CVSourceCoverageDiagnostics,
    CVTailoringDiagnostics,
)
from app.services.tailored_cv_metadata import (
    issue_tailoring_entitlement_v3,
    verify_tailoring_entitlement_v3,
)


@pytest.fixture
def sample_source_document() -> CVDocumentV2:
    return CVDocumentV2(
        schema_version=2,
        extraction_version="1.0.0",
        parser_version="1.0.0",
        reconstruction_version=4,
        requires_reprocessing=False,
        identity=CVIdentity(full_name="Jane Smith", email="jane@example.com"),
        summary=CVParagraphBlock(
            block_id="b1",
            text="Python Developer with 4 years experience.",
            source_block_ids=["b1"],
            origin=ContentOrigin.EXTRACTED,
        ),
        sections=[],
        reconstruction_diagnostics=CVReconstructionDiagnostics(
            reconstruction_version=4,
            warnings=[],
            block_confidence={"b1": 1.0},
            source_coverage=CVSourceCoverageDiagnostics(
                raw_block_count=1,
                accounted_block_count=1,
                significant_character_count=40,
                mapped_character_count=40,
                coverage_ratio=1.0,
            ),
        ),
    )


@pytest.mark.asyncio
async def test_v3_entitlement_tampering_of_tailored_document_rejected(
    sample_source_document, monkeypatch
):
    """Tampering with tailored document content invalidates V3 entitlement signature."""
    import hashlib

    from app.services.tailored_cv_metadata import canonical_source_document_hash

    user_id = uuid4()
    tailored = sample_source_document.model_copy(deep=True)
    cv_text = "Python Developer with 4 years experience."
    jd_text = "Python Dev JD"
    src_hash = canonical_source_document_hash(sample_source_document)
    jd_hash = hashlib.sha256(jd_text.encode("utf-8")).hexdigest()
    diag = CVTailoringDiagnostics(
        source_document_hash=src_hash,
        jd_hash=jd_hash,
        accepted_count=0,
        rejected_count=0,
        preserved_count=1,
        decisions=[],
    )

    entitlement = issue_tailoring_entitlement_v3(
        user_id,
        cv_text,
        jd_text,
        sample_source_document,
        tailored,
        diag,
    )

    # Tampered tailored document (changed text without user_edit entitlement update)
    tampered_tailored = tailored.model_copy(deep=True)
    tampered_tailored.identity.full_name = "Tampered hacker name."

    with pytest.raises(ValueError, match="Invalid tailoring entitlement"):
        verify_tailoring_entitlement_v3(
            entitlement,
            user_id,
            cv_text,
            jd_text,
            sample_source_document,
            tampered_tailored,
            diag,
        )


def test_v3_entitlement_tampering_of_source_document_rejected(sample_source_document):
    """Tampering with source document invalidates V3 entitlement signature."""
    import hashlib

    from app.services.tailored_cv_metadata import canonical_source_document_hash

    user_id = uuid4()
    tailored = sample_source_document.model_copy(deep=True)
    cv_text = "Python Developer with 4 years experience."
    jd_text = "Python Dev JD"
    src_hash = canonical_source_document_hash(sample_source_document)
    jd_hash = hashlib.sha256(jd_text.encode("utf-8")).hexdigest()
    diag = CVTailoringDiagnostics(
        source_document_hash=src_hash,
        jd_hash=jd_hash,
        accepted_count=0,
        rejected_count=0,
        preserved_count=1,
        decisions=[],
    )

    entitlement = issue_tailoring_entitlement_v3(
        user_id,
        cv_text,
        jd_text,
        sample_source_document,
        tailored,
        diag,
    )

    tampered_source = sample_source_document.model_copy(deep=True)
    tampered_source.identity.full_name = "Tampered Source Name"

    with pytest.raises(ValueError, match=r"Invalid tailoring.*source hash"):
        verify_tailoring_entitlement_v3(
            entitlement,
            user_id,
            "Python Developer with 4 years experience.",
            "Python Dev JD",
            tampered_source,
            tailored,
            diag,
        )
