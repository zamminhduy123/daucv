import hashlib
from uuid import UUID

import pytest

from app.models.cv_document_v2 import (
    CVDocumentV2,
    CVIdentity,
    CVTailoringDiagnostics,
)
from app.services import tailored_cv_metadata
from app.services.tailored_cv_metadata import (
    canonical_source_document_hash,
    issue_pipeline_source_ticket,
    issue_tailoring_entitlement,
    issue_tailoring_entitlement_v2,
    issue_tailoring_entitlement_v3,
    verify_pipeline_source_ticket,
    verify_tailoring_entitlement,
    verify_tailoring_entitlement_v2,
    verify_tailoring_entitlement_v3,
)

USER_ID = UUID("11111111-1111-1111-1111-111111111111")
OTHER_USER_ID = UUID("22222222-2222-2222-2222-222222222222")


def test_tailoring_entitlement_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEXTAUTH_SECRET", "test-secret")

    entitlement = issue_tailoring_entitlement(USER_ID, "source CV", "target JD")

    assert (
        verify_tailoring_entitlement(entitlement, USER_ID, "source CV", "target JD")
        == hashlib.sha256(entitlement.encode()).hexdigest()
    )


@pytest.mark.parametrize(
    ("user_id", "cv_text", "jd_text"),
    [
        (OTHER_USER_ID, "source CV", "target JD"),
        (USER_ID, "different CV", "target JD"),
        (USER_ID, "source CV", "different JD"),
    ],
)
def test_tailoring_entitlement_rejects_wrong_binding(
    monkeypatch: pytest.MonkeyPatch,
    user_id: UUID,
    cv_text: str,
    jd_text: str,
) -> None:
    monkeypatch.setenv("NEXTAUTH_SECRET", "test-secret")
    entitlement = issue_tailoring_entitlement(USER_ID, "source CV", "target JD")

    with pytest.raises(ValueError, match="Invalid tailoring entitlement"):
        verify_tailoring_entitlement(entitlement, user_id, cv_text, jd_text)


def test_tailoring_entitlement_rejects_tampering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NEXTAUTH_SECRET", "test-secret")
    entitlement = issue_tailoring_entitlement(USER_ID, "source CV", "target JD")
    tampered = f"{entitlement[:-1]}{'0' if entitlement[-1] != '0' else '1'}"

    with pytest.raises(ValueError, match="Invalid tailoring entitlement"):
        verify_tailoring_entitlement(tampered, USER_ID, "source CV", "target JD")


def test_issue_and_verify_tailoring_entitlement_v2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NEXTAUTH_SECRET", "test-secret")
    doc = CVDocumentV2(identity=CVIdentity(full_name="John Doe"))
    entitlement = issue_tailoring_entitlement_v2(USER_ID, "source CV", "target JD", doc)

    assert (
        verify_tailoring_entitlement_v2(
            entitlement, USER_ID, "source CV", "target JD", doc
        )
        == hashlib.sha256(entitlement.encode()).hexdigest()
    )


def test_pipeline_source_ticket_binds_source_document_and_raw_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NEXTAUTH_SECRET", "test-secret")
    monkeypatch.setattr(tailored_cv_metadata.time, "time", lambda: 1_000)
    document = CVDocumentV2(identity=CVIdentity(full_name="John Doe"))
    ticket = issue_pipeline_source_ticket(
        USER_ID,
        "source CV",
        document,
        "11111111-1111-4111-8111-111111111111",
    )

    assert verify_pipeline_source_ticket(
        ticket,
        USER_ID,
        "source CV",
        document,
        "11111111-1111-4111-8111-111111111111",
    )

    with pytest.raises(ValueError, match="no longer matches"):
        verify_pipeline_source_ticket(
            ticket,
            USER_ID,
            "source CV",
            document,
            None,
        )


def test_v2_entitlement_source_document_hash_tampering_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NEXTAUTH_SECRET", "test-secret")
    doc = CVDocumentV2(identity=CVIdentity(full_name="John Doe"))
    tampered_doc = CVDocumentV2(identity=CVIdentity(full_name="Tampered Name"))
    entitlement = issue_tailoring_entitlement_v2(USER_ID, "source CV", "target JD", doc)

    with pytest.raises(ValueError, match="Invalid tailoring entitlement"):
        verify_tailoring_entitlement_v2(
            entitlement, USER_ID, "source CV", "target JD", tampered_doc
        )


def test_v2_entitlement_user_mismatch_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEXTAUTH_SECRET", "test-secret")
    doc = CVDocumentV2(identity=CVIdentity(full_name="John Doe"))
    entitlement = issue_tailoring_entitlement_v2(USER_ID, "source CV", "target JD", doc)

    with pytest.raises(ValueError, match="Invalid tailoring entitlement"):
        verify_tailoring_entitlement_v2(
            entitlement, OTHER_USER_ID, "source CV", "target JD", doc
        )


def test_legacy_entitlement_cannot_verify_v2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEXTAUTH_SECRET", "test-secret")
    legacy_entitlement = issue_tailoring_entitlement(USER_ID, "source CV", "target JD")
    doc = CVDocumentV2(identity=CVIdentity(full_name="John Doe"))

    with pytest.raises(ValueError, match="Invalid tailoring entitlement"):
        verify_tailoring_entitlement_v2(
            legacy_entitlement, USER_ID, "source CV", "target JD", doc
        )


def _v3_fixture() -> tuple[CVDocumentV2, CVDocumentV2, CVTailoringDiagnostics]:
    source = CVDocumentV2(identity=CVIdentity(full_name="Synthetic Candidate"))
    tailored = source.model_copy(deep=True)
    diagnostics = CVTailoringDiagnostics(
        source_document_hash=canonical_source_document_hash(source),
        jd_hash=hashlib.sha256(b"target JD").hexdigest(),
    )
    return source, tailored, diagnostics


def test_v3_entitlement_binds_inputs_diagnostics_and_expiry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NEXTAUTH_SECRET", "test-secret")
    monkeypatch.setattr(tailored_cv_metadata.time, "time", lambda: 1_000)
    source, tailored, diagnostics = _v3_fixture()
    entitlement = issue_tailoring_entitlement_v3(
        USER_ID,
        "source CV",
        "target JD",
        source,
        tailored,
        diagnostics,
    )
    analysis_key = entitlement.split(".")[2]
    assert (
        verify_tailoring_entitlement_v3(
            entitlement,
            USER_ID,
            "source CV",
            "target JD",
            source,
            tailored,
            diagnostics,
        )
        == analysis_key
    )

    with pytest.raises(ValueError, match="binding"):
        verify_tailoring_entitlement_v3(
            entitlement,
            USER_ID,
            "changed CV",
            "target JD",
            source,
            tailored,
            diagnostics,
        )
    with pytest.raises(ValueError, match="required"):
        verify_tailoring_entitlement_v3(
            entitlement,
            USER_ID,
            "source CV",
            "target JD",
            source,
            tailored,
            None,  # type: ignore[arg-type]
        )

    monkeypatch.setattr(tailored_cv_metadata.time, "time", lambda: 87_401)
    with pytest.raises(ValueError, match="expired"):
        verify_tailoring_entitlement_v3(
            entitlement,
            USER_ID,
            "source CV",
            "target JD",
            source,
            tailored,
            diagnostics,
        )
