import hashlib
import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.models.cv_document_v2 import (
    ContentOrigin,
    CVDocumentV2,
    CVIdentity,
    CVParagraphBlock,
    CVReconstructionDiagnostics,
    CVRewriteDecision,
    CVSection,
    CVSourceCoverageDiagnostics,
    CVTailoringDiagnostics,
)
from app.schemas.tailored_cv import TailoredCV, TailoredCVVersionCreate
from app.services import tailored_cv_service
from app.services.cv_tailoring_service import hash_field_value
from app.services.tailored_cv_metadata import (
    canonical_source_document_hash,
    issue_tailoring_entitlement_v3,
)
from app.services.tailored_cv_service import TailoredCVEntitlementError

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


def _valid_source_doc(name: str = "Server Source") -> CVDocumentV2:
    return CVDocumentV2(
        identity=CVIdentity(full_name=name),
        sections=[
            CVSection(
                id="s1",
                type="experience",
                title="Experience",
                confidence=1.0,
                source_block_ids=["b1"],
                blocks=[],
            )
        ],
        reconstruction_diagnostics=CVReconstructionDiagnostics(
            source_coverage=CVSourceCoverageDiagnostics(
                raw_block_count=1,
                accounted_block_count=1,
                significant_character_count=1,
                mapped_character_count=1,
                coverage_ratio=1.0,
            )
        ),
    )


def _legacy_row(*, current: bool = False) -> dict:
    doc = _valid_source_doc("Duy")
    if not current:
        doc.reconstruction_version = 3
        doc.requires_reprocessing = True
        doc.reconstruction_warnings = ["legacy_source_requires_reprocessing"]
    return {
        "id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
        "user_id": USER_ID,
        "version_number": 1,
        "tailored_cv": {"name": "Duy", "sections": []},
        "source_cv_text": "Duy\nBackend Developer",
        "jd_text": "Backend Engineer role",
        "selected_design": "classic_ats",
        "tailoring_entitlement": "entitlement",
        "created_at": "2026-03-30T00:00:00Z",
        "updated_at": "2026-03-30T00:00:00Z",
        "document_schema_version": 2,
        "reconstruction_version": doc.reconstruction_version,
        "document_v2": doc.model_dump(),
        "source_document_v2": doc.model_dump(),
        "source_pdf_reference": "duy.pdf",
        "source_raw_text": "Duy\nBackend Developer",
        "source_normalized_text": "Duy\nBackend Developer",
        "source_hash": "hash",
        "jd_hash": "hash",
        "reconstruction_warnings": doc.reconstruction_warnings,
    }


@pytest.mark.asyncio
async def test_create_version_requires_v2_persistence_migrations() -> None:
    request = TailoredCVVersionCreate(
        tailored_cv=TailoredCV(name="Duy", sections=[]),
        source_cv_text="Duy\nBackend Developer\nEXPERIENCE\nBackend Developer at Acme",
        jd_text="Backend Engineer role",
        selected_design="classic_ats",
        tailoring_entitlement="x" * 65,
    )
    fetch_one = AsyncMock(
        side_effect=[{"id": USER_ID, "cv_filename": None}, KeyError("document_v2")],
    )

    with (
        patch.object(tailored_cv_service.Database, "fetch_one", fetch_one),
        patch.object(
            tailored_cv_service,
            "verify_tailoring_entitlement",
            return_value="analysis-key",
        ),
        patch.object(
            tailored_cv_service,
            "build_source_preserving_tailored_cv_from_parts",
            return_value=request.tailored_cv,
        ),
        pytest.raises(RuntimeError, match="V2 document persistence columns missing"),
    ):
        await tailored_cv_service.create_version(USER_ID, request)


@pytest.mark.asyncio
async def test_create_version_rejects_replayed_entitlement() -> None:
    request = TailoredCVVersionCreate(
        tailored_cv=TailoredCV(name="Duy", sections=[]),
        source_cv_text="Duy\nBackend Developer",
        jd_text="Backend Engineer role",
        selected_design="classic_ats",
        tailoring_entitlement="x" * 65,
    )
    fetch_one = AsyncMock(return_value={"id": USER_ID, "cv_filename": None})

    with (
        patch.object(tailored_cv_service.Database, "fetch_one", fetch_one),
        patch.object(
            tailored_cv_service,
            "verify_tailoring_entitlement",
            side_effect=ValueError("Invalid tailoring entitlement"),
        ),
        pytest.raises(TailoredCVEntitlementError),
    ):
        await tailored_cv_service.create_version(USER_ID, request)


@pytest.mark.asyncio
async def test_create_version_persists_v2_and_source_artifacts_by_default() -> None:
    untrusted_document = _valid_source_doc("Client override")
    request = TailoredCVVersionCreate(
        tailored_cv=TailoredCV(name="Duy", sections=[]),
        source_cv_text="Duy\nBackend Developer\nSKILLS\nBackend: Python, FastAPI",
        jd_text="Backend Engineer role",
        selected_design="classic_ats",
        tailoring_entitlement="x" * 65,
        document_v2=untrusted_document,
        source_document_v2=untrusted_document,
    )
    saved_row = _legacy_row()
    fetch_one = AsyncMock(
        side_effect=[{"id": USER_ID, "cv_filename": "duy.pdf"}, saved_row],
    )

    with (
        patch.object(tailored_cv_service.Database, "fetch_one", fetch_one),
        patch.object(
            tailored_cv_service,
            "verify_tailoring_entitlement",
            return_value="analysis-key",
        ),
        patch.object(
            tailored_cv_service,
            "build_source_preserving_tailored_cv_from_parts",
            return_value=request.tailored_cv,
        ),
    ):
        version = await tailored_cv_service.create_version(USER_ID, request)

    insert_call = fetch_one.await_args_list[1]
    assert "source_document_v2" in insert_call.args[0]
    assert "source_raw_text" in insert_call.args[0]
    assert request.source_cv_text in insert_call.args
    assert version.document_schema_version == 2
    assert version.source_document_v2 is not None
    assert version.source_pdf_reference == "duy.pdf"


@pytest.mark.asyncio
async def test_create_version_with_v2_entitlement_success() -> None:
    source_document = _valid_source_doc("Server Source")
    v2_entitlement = f"v2.{'a' * 32}.{'b' * 64}.{'c' * 64}.{'d' * 64}"
    request = TailoredCVVersionCreate(
        tailored_cv=TailoredCV(name="Duy", sections=[]),
        source_cv_text="Duy\nBackend Developer",
        jd_text="Backend Engineer role",
        selected_design="classic_ats",
        tailoring_entitlement=v2_entitlement,
        document_v2=_valid_source_doc("Duy"),
        source_document_v2=source_document,
    )
    fetch_one = AsyncMock(
        side_effect=[
            {"id": USER_ID, "cv_filename": "duy.pdf"},
            _legacy_row(current=True),
        ],
    )

    with (
        patch.object(tailored_cv_service.Database, "fetch_one", fetch_one),
        patch.object(
            tailored_cv_service,
            "verify_tailoring_entitlement_v2",
            return_value="analysis-key",
        ) as verify_mock,
        patch.object(
            tailored_cv_service,
            "build_source_preserving_tailored_cv_from_parts",
            return_value=request.tailored_cv,
        ),
    ):
        await tailored_cv_service.create_version(USER_ID, request)

    verify_mock.assert_called_once_with(
        request.tailoring_entitlement,
        USER_ID,
        request.source_cv_text,
        request.jd_text,
        source_document,
    )


@pytest.mark.asyncio
async def test_create_version_with_v2_entitlement_tampered_doc_rejected() -> None:
    source_document = _valid_source_doc("Tampered Source")
    v2_entitlement = f"v2.{'a' * 32}.{'b' * 64}.{'c' * 64}.{'d' * 64}"
    request = TailoredCVVersionCreate(
        tailored_cv=TailoredCV(name="Duy", sections=[]),
        source_cv_text="Duy\nBackend Developer",
        jd_text="Backend Engineer role",
        selected_design="classic_ats",
        tailoring_entitlement=v2_entitlement,
        document_v2=_valid_source_doc("Duy"),
        source_document_v2=source_document,
    )
    fetch_one = AsyncMock(
        side_effect=[{"id": USER_ID, "cv_filename": "duy.pdf"}],
    )

    with (
        patch.object(tailored_cv_service.Database, "fetch_one", fetch_one),
        patch.object(
            tailored_cv_service,
            "verify_tailoring_entitlement_v2",
            side_effect=ValueError("Invalid tailoring entitlement"),
        ),
        pytest.raises(TailoredCVEntitlementError),
    ):
        await tailored_cv_service.create_version(USER_ID, request)


@pytest.mark.asyncio
async def test_create_version_with_legacy_entitlement_ignores_client_doc() -> None:
    source_document = _valid_source_doc("Client Mock")
    legacy_entitlement = f"{'a' * 32}.{'b' * 64}.{'c' * 64}"
    request = TailoredCVVersionCreate(
        tailored_cv=TailoredCV(name="Duy", sections=[]),
        source_cv_text="Duy\nBackend Developer\nSKILLS\nPython",
        jd_text="Backend Engineer role",
        selected_design="classic_ats",
        tailoring_entitlement=legacy_entitlement,
        document_v2=_valid_source_doc("Duy"),
        source_document_v2=source_document,
    )
    fetch_one = AsyncMock(
        side_effect=[{"id": USER_ID, "cv_filename": "duy.pdf"}, _legacy_row()],
    )

    with (
        patch.object(tailored_cv_service.Database, "fetch_one", fetch_one),
        patch.object(
            tailored_cv_service,
            "verify_tailoring_entitlement",
            return_value="analysis-key",
        ) as verify_mock,
        patch.object(
            tailored_cv_service,
            "build_source_preserving_tailored_cv_from_parts",
            return_value=request.tailored_cv,
        ),
    ):
        await tailored_cv_service.create_version(USER_ID, request)

    verify_mock.assert_called_once_with(
        request.tailoring_entitlement,
        USER_ID,
        request.source_cv_text,
        request.jd_text,
    )

    insert_args = fetch_one.await_args_list[1].args
    persisted_source = json.loads(insert_args[15])
    assert insert_args[11] == 3
    assert persisted_source["requires_reprocessing"] is True
    assert persisted_source["reconstruction_version"] == 3
    assert (
        "legacy_source_requires_reprocessing"
        in persisted_source["reconstruction_warnings"]
    )
    assert (
        "legacy_entitlement_source_document_ignored"
        in persisted_source["reconstruction_warnings"]
    )


@pytest.mark.asyncio
async def test_v3_save_persists_exact_signed_document_and_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NEXTAUTH_SECRET", "test-secret")
    source = _valid_source_doc("Synthetic Candidate")
    source.summary = CVParagraphBlock(
        block_id="summary-1",
        text="Supported internal reporting.",
        source_block_ids=["b1"],
    )
    tailored = source.model_copy(deep=True)
    assert tailored.summary is not None
    tailored.summary.text = "Internal reporting supported."
    tailored.summary.origin = ContentOrigin.LLM_REWRITE
    tailored.summary.original_values = {"text": source.summary.text}
    tailored.summary.tailored_values = {"text": tailored.summary.text}
    original_hash = hash_field_value(source.summary.text)
    proposed_hash = hash_field_value(tailored.summary.text)
    diagnostics = CVTailoringDiagnostics(
        source_document_hash=canonical_source_document_hash(source),
        jd_hash=hashlib.sha256(b"Backend role").hexdigest(),
        accepted_count=1,
        decisions=[
            CVRewriteDecision(
                operation_id="summary-edit",
                block_id="summary-1",
                field="text",
                status="accepted",
                original_value_hash=original_hash,
                proposed_value_hash=proposed_hash,
            )
        ],
    )
    entitlement = issue_tailoring_entitlement_v3(
        USER_ID,
        "Synthetic CV",
        "Backend role",
        source,
        tailored,
        diagnostics,
    )
    request = TailoredCVVersionCreate(
        tailored_cv=TailoredCV(name="Synthetic Candidate", sections=[]),
        source_cv_text="Synthetic CV",
        jd_text="Backend role",
        selected_design="classic_ats",
        tailoring_entitlement=entitlement,
        document_v2=tailored,
        source_document_v2=source,
        tailoring_diagnostics=diagnostics,
    )
    saved_row = _legacy_row(current=True)
    saved_row.update(
        {
            "document_v2": tailored.model_dump(mode="json"),
            "source_document_v2": source.model_dump(mode="json"),
            "tailoring_diagnostics": diagnostics.model_dump(mode="json"),
            "reconstruction_version": tailored.reconstruction_version,
        }
    )
    fetch_one = AsyncMock(
        side_effect=[
            {"id": USER_ID, "cv_filename": "synthetic.pdf"},
            saved_row,
        ],
    )
    with (
        patch.object(tailored_cv_service.Database, "fetch_one", fetch_one),
        patch.object(
            tailored_cv_service,
            "build_source_preserving_tailored_cv_from_parts",
            return_value=request.tailored_cv,
        ),
    ):
        version = await tailored_cv_service.create_version(USER_ID, request)

    insert_args = fetch_one.await_args_list[1].args
    assert insert_args[8] == entitlement.split(".")[2]
    assert json.loads(insert_args[9]) == tailored.model_dump(mode="json")
    assert json.loads(insert_args[19]) == diagnostics.model_dump(mode="json")
    assert version.document_v2 == tailored
    assert version.tailoring_diagnostics == diagnostics
