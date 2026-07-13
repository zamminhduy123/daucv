from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest

from app.models.domain import TailoredCV
from app.schemas.tailored_cv import TailoredCVVersionCreate
from app.services import tailored_cv_service

USER_ID = UUID("11111111-1111-1111-1111-111111111111")
VERSION_ID = UUID("22222222-2222-2222-2222-222222222222")


class UndefinedColumnError(Exception):
    sqlstate = "42703"


def _legacy_row() -> dict:
    now = datetime.now(UTC)
    return {
        "id": VERSION_ID,
        "source_cv_id": None,
        "target_role": "Backend Engineer",
        "company_name": "Example Co",
        "jd_text": "Backend Engineer role",
        "tailored_cv": {"name": "Duy", "sections": []},
        "selected_design": "classic_ats",
        "created_at": now,
        "updated_at": now,
    }


@pytest.mark.asyncio
async def test_get_version_falls_back_when_v2_columns_are_not_migrated() -> None:
    fetch_one = AsyncMock(
        side_effect=[
            UndefinedColumnError('column "document_v2" does not exist'),
            _legacy_row(),
        ]
    )

    with patch.object(tailored_cv_service.Database, "fetch_one", fetch_one):
        version = await tailored_cv_service.get_version(VERSION_ID, USER_ID)

    assert version.id == VERSION_ID
    assert version.document_v2 is None
    assert version.document_schema_version == 1
    assert fetch_one.await_count == 2
    assert "document_v2" in fetch_one.await_args_list[0].args[0]
    assert "document_v2" not in fetch_one.await_args_list[1].args[0]


@pytest.mark.asyncio
async def test_create_version_falls_back_to_legacy_columns() -> None:
    request = TailoredCVVersionCreate(
        tailored_cv=TailoredCV(name="Duy", sections=[]),
        source_cv_text="Duy\nduy@example.com",
        jd_text="Backend Engineer role",
        selected_design="classic_ats",
        tailoring_entitlement="x" * 65,
    )
    fetch_one = AsyncMock(
        side_effect=[
            None,
            UndefinedColumnError('column "document_schema_version" does not exist'),
            _legacy_row(),
        ]
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

    assert version.id == VERSION_ID
    assert fetch_one.await_count == 3
    assert "document_v2" in fetch_one.await_args_list[1].args[0]
    assert "document_v2" not in fetch_one.await_args_list[2].args[0]


@pytest.mark.asyncio
async def test_list_versions_falls_back_to_legacy_columns() -> None:
    fetch_all = AsyncMock(
        side_effect=[
            UndefinedColumnError('column "reconstruction_version" does not exist'),
            [_legacy_row()],
        ]
    )

    with patch.object(tailored_cv_service.Database, "fetch_all", fetch_all):
        versions = await tailored_cv_service.list_versions(USER_ID)

    assert [version.id for version in versions] == [VERSION_ID]
    assert fetch_all.await_count == 2
    assert "document_v2" not in fetch_all.await_args_list[1].args[0]


@pytest.mark.asyncio
async def test_update_design_falls_back_to_legacy_columns() -> None:
    fetch_one = AsyncMock(
        side_effect=[
            UndefinedColumnError('column "reconstruction_warnings" does not exist'),
            {**_legacy_row(), "selected_design": "modern_professional"},
        ]
    )

    with patch.object(tailored_cv_service.Database, "fetch_one", fetch_one):
        version = await tailored_cv_service.update_design(
            VERSION_ID, USER_ID, "modern_professional"
        )

    assert version.selected_design == "modern_professional"
    assert fetch_one.await_count == 2
    assert fetch_one.await_args_list[1].args[1:] == (
        "modern_professional",
        VERSION_ID,
        USER_ID,
    )


@pytest.mark.asyncio
async def test_get_version_prefers_v2_columns_when_available() -> None:
    fetch_one = AsyncMock(return_value=_legacy_row())

    with patch.object(tailored_cv_service.Database, "fetch_one", fetch_one):
        await tailored_cv_service.get_version(VERSION_ID, USER_ID)

    fetch_one.assert_awaited_once()
    assert "document_v2" in fetch_one.await_args.args[0]


@pytest.mark.asyncio
async def test_get_version_does_not_hide_unrelated_undefined_column() -> None:
    error = UndefinedColumnError('column "selected_desgin" does not exist')
    fetch_one = AsyncMock(side_effect=error)

    with (
        patch.object(tailored_cv_service.Database, "fetch_one", fetch_one),
        pytest.raises(UndefinedColumnError, match="selected_desgin"),
    ):
        await tailored_cv_service.get_version(VERSION_ID, USER_ID)

    fetch_one.assert_awaited_once()
