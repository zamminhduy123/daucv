import hashlib
from uuid import UUID

import pytest

from app.services.tailored_cv_metadata import (
    issue_tailoring_entitlement,
    verify_tailoring_entitlement,
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
