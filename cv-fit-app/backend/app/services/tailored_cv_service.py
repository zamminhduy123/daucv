import json
from uuid import UUID

from app.core.db import Database
from app.schemas.tailored_cv import (
    CVDesign,
    TailoredCVVersionCreate,
    TailoredCVVersionResponse,
)
from app.services.cv_quality_checks import (
    build_source_preserving_tailored_cv_from_parts,
)
from app.services.tailored_cv_metadata import extract_target_metadata

VERSION_COLUMNS = "id, source_cv_id, target_role, company_name, jd_text, tailored_cv, selected_design, created_at, updated_at"


class TailoredCVNotFoundError(Exception):
    pass


def _tailored_version(row: dict) -> TailoredCVVersionResponse:
    data = dict(row)
    if isinstance(data.get("tailored_cv"), str):
        data["tailored_cv"] = json.loads(data["tailored_cv"])
    return TailoredCVVersionResponse.model_validate(data)


async def create_version(
    user_id: UUID, request: TailoredCVVersionCreate
) -> TailoredCVVersionResponse:
    source = await Database.fetch_one(
        "SELECT id FROM public.user_cvs WHERE user_id = $1 AND is_active = TRUE LIMIT 1",
        user_id,
    )
    inferred_role, inferred_company = extract_target_metadata(request.jd_text)
    complete_cv = build_source_preserving_tailored_cv_from_parts(
        cv_text=request.source_cv_text,
        headline=request.tailored_cv.headline,
        suggested_edits=request.suggested_edits,
        candidate_cv=request.tailored_cv,
    )
    row = await Database.fetch_one(
        """INSERT INTO public.tailored_cv_versions (user_id, source_cv_id, target_role, company_name, jd_text, tailored_cv, selected_design)
           VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7)
           RETURNING {VERSION_COLUMNS}""",
        user_id,
        source["id"] if source else None,
        request.target_role or inferred_role,
        request.company_name or inferred_company,
        request.jd_text,
        json.dumps(complete_cv.model_dump()),
        request.selected_design,
    )
    return _tailored_version(row)


async def list_versions(user_id: UUID) -> list[TailoredCVVersionResponse]:
    rows = await Database.fetch_all(
        f"SELECT {VERSION_COLUMNS} FROM public.tailored_cv_versions WHERE user_id = $1 ORDER BY created_at DESC",
        user_id,
    )
    return [_tailored_version(row) for row in rows]


async def get_version(version_id: UUID, user_id: UUID) -> TailoredCVVersionResponse:
    row = await Database.fetch_one(
        f"SELECT {VERSION_COLUMNS} FROM public.tailored_cv_versions WHERE id = $1 AND user_id = $2",
        version_id,
        user_id,
    )
    if not row:
        raise TailoredCVNotFoundError
    return _tailored_version(row)


async def update_design(
    version_id: UUID, user_id: UUID, selected_design: CVDesign
) -> TailoredCVVersionResponse:
    row = await Database.fetch_one(
        """UPDATE public.tailored_cv_versions SET selected_design = $1, updated_at = now()
           WHERE id = $2 AND user_id = $3
           RETURNING {VERSION_COLUMNS}""",
        selected_design,
        version_id,
        user_id,
    )
    if not row:
        raise TailoredCVNotFoundError
    return _tailored_version(row)


async def delete_version(version_id: UUID, user_id: UUID) -> None:
    deleted = await Database.execute(
        "DELETE FROM public.tailored_cv_versions WHERE id = $1 AND user_id = $2",
        version_id,
        user_id,
    )
    if deleted == "DELETE 0":
        raise TailoredCVNotFoundError
