import json
import logging
from uuid import UUID

from app.core.db import Database
from app.models.domain import TailoredCV
from app.schemas.tailored_cv import (
    CVDesign,
    TailoredCVVersionCreate,
    TailoredCVVersionResponse,
)
from app.services.cv_language import detect_tailored_cv_language
from app.services.cv_quality_checks import (
    build_source_preserving_tailored_cv_from_parts,
)
from app.services.cv_v1_adapter import v1_to_v2_safe
from app.services.tailored_cv_metadata import (
    extract_target_metadata,
    verify_tailoring_entitlement,
)

VERSION_COLUMNS = "id, source_cv_id, target_role, company_name, jd_text, tailored_cv, document_v2, selected_design, document_schema_version, reconstruction_version, source_hash, jd_hash, reconstruction_warnings, created_at, updated_at"
LEGACY_VERSION_COLUMNS = "id, source_cv_id, target_role, company_name, jd_text, tailored_cv, selected_design, created_at, updated_at"
PHASE_ONE_VERSION_COLUMNS = (
    "document_v2",
    "document_schema_version",
    "reconstruction_version",
    "source_hash",
    "jd_hash",
    "reconstruction_warnings",
)

logger = logging.getLogger(__name__)


class TailoredCVNotFoundError(Exception):
    pass


class TailoredCVEntitlementError(Exception):
    pass


class TailoredCVEntitlementUsedError(Exception):
    pass


class UnsupportedCVSchemaVersionError(ValueError):
    def __init__(self, schema_version: int) -> None:
        self.schema_version = schema_version
        super().__init__(f"Unsupported CV document schema version: {schema_version}")


def _phase_one_columns_missing(exc: Exception) -> bool:
    """Allow the export feature to run while migration 003 is rolling out."""
    message = str(exc).lower()
    return getattr(exc, "sqlstate", None) == "42703" and any(
        column in message for column in PHASE_ONE_VERSION_COLUMNS
    )


async def _fetch_version_row(
    query: str, legacy_query: str, *args: object
) -> dict | None:
    try:
        return await Database.fetch_one(query, *args)
    except Exception as exc:
        if not _phase_one_columns_missing(exc):
            raise
        logger.warning(
            "CV document V2 columns are unavailable; using temporary V1 compatibility path"
        )
        return await Database.fetch_one(legacy_query, *args)


async def _fetch_version_rows(
    query: str, legacy_query: str, *args: object
) -> list[dict]:
    try:
        return await Database.fetch_all(query, *args)
    except Exception as exc:
        if not _phase_one_columns_missing(exc):
            raise
        logger.warning(
            "CV document V2 columns are unavailable; using temporary V1 compatibility path"
        )
        return await Database.fetch_all(legacy_query, *args)


def _tailored_version(row: dict) -> TailoredCVVersionResponse:
    data = dict(row)
    tailored_cv_data = data.pop("tailored_cv", None)
    document_v2_data = data.pop("document_v2", None)
    schema_version = data.pop("document_schema_version", 1)
    if isinstance(tailored_cv_data, str):
        tailored_cv_data = json.loads(tailored_cv_data)
    if isinstance(document_v2_data, str):
        document_v2_data = json.loads(document_v2_data)
    if tailored_cv_data:
        data["source_language"] = detect_tailored_cv_language(
            TailoredCV.model_validate(tailored_cv_data)
        )
    return normalize_version(
        tailored_cv_data=tailored_cv_data,
        document_v2_data=document_v2_data,
        schema_version=schema_version,
        **data,
    )


def normalize_version(
    tailored_cv_data: dict,
    document_v2_data: dict | None,
    schema_version: int,
    **extra: object,
) -> TailoredCVVersionResponse:
    """Return a version-aware ``TailoredCVVersionResponse``.

    * ``schema_version == 2`` and ``document_v2`` present → use V2 document.
    * ``schema_version == 1`` or missing ``document_v2`` → adapt V1 → V2
      for rendering.  The stored ``document_schema_version`` is preserved.

    Extra keyword arguments are merged into the model payload (e.g.
    ``id``, ``selected_design``, ``created_at``).
    """
    if schema_version not in (1, 2):
        raise UnsupportedCVSchemaVersionError(schema_version)
    if schema_version == 2 and document_v2_data is None:
        raise UnsupportedCVSchemaVersionError(schema_version)

    effective_document_v2 = document_v2_data if schema_version == 2 else None
    response = TailoredCVVersionResponse.model_validate(
        {
            "tailored_cv": tailored_cv_data,
            "document_v2": effective_document_v2,
            "document_schema_version": schema_version,
            **extra,
        }
    )

    # If we have V2, it's ready. If not, build a V2 from V1 on the fly.
    if schema_version == 2:
        return response

    # Build V2 from V1 adapter (never discards content, never invents).
    if tailored_cv_data:
        v1_doc = TailoredCV.model_validate(tailored_cv_data)
        v2_doc = v1_to_v2_safe(v1_doc)
        if v2_doc:
            response.document_v2 = v2_doc

    return response


async def create_version(
    user_id: UUID, request: TailoredCVVersionCreate
) -> TailoredCVVersionResponse:
    try:
        analysis_key = verify_tailoring_entitlement(
            request.tailoring_entitlement,
            user_id,
            request.source_cv_text,
            request.jd_text,
        )
    except ValueError as exc:
        raise TailoredCVEntitlementError from exc

    source = await Database.fetch_one(
        "SELECT id FROM public.user_cvs WHERE user_id = $1 AND cv_text = $2 ORDER BY is_active DESC, created_at DESC LIMIT 1",
        user_id,
        request.source_cv_text,
    )
    inferred_role, inferred_company = extract_target_metadata(request.jd_text)
    complete_cv = build_source_preserving_tailored_cv_from_parts(
        cv_text=request.source_cv_text,
        headline=request.tailored_cv.headline,
        suggested_edits=request.suggested_edits,
        candidate_cv=request.tailored_cv,
    )

    import hashlib

    source_hash = (
        hashlib.sha256(request.source_cv_text.encode("utf-8")).hexdigest()
        if request.source_cv_text
        else None
    )
    jd_hash = (
        hashlib.sha256(request.jd_text.encode("utf-8")).hexdigest()
        if request.jd_text
        else None
    )

    document_v2_json = None
    schema_version = 1
    reconstruction_version = 1
    reconstruction_warnings = []

    if request.document_v2 is not None:
        document_v2_json = json.dumps(request.document_v2.model_dump())
        schema_version = 2

    legacy_args = (
        user_id,
        source["id"] if source else None,
        request.target_role or inferred_role,
        request.company_name or inferred_company,
        request.jd_text,
        json.dumps(complete_cv.model_dump()),
        request.selected_design,
        analysis_key,
    )
    try:
        try:
            row = await Database.fetch_one(
                f"""INSERT INTO public.tailored_cv_versions (
                       user_id, source_cv_id, target_role, company_name, jd_text,
                       tailored_cv, selected_design, analysis_key,
                       document_v2, document_schema_version, reconstruction_version,
                       source_hash, jd_hash, reconstruction_warnings
                   )
                   VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, $9::jsonb, $10, $11, $12, $13, $14)
                   RETURNING {VERSION_COLUMNS}""",
                *legacy_args,
                document_v2_json,
                schema_version,
                reconstruction_version,
                source_hash,
                jd_hash,
                reconstruction_warnings,
            )
        except Exception as exc:
            if not _phase_one_columns_missing(exc):
                raise
            logger.warning(
                "CV document V2 columns are unavailable; saving through temporary V1 compatibility path"
            )
            row = await Database.fetch_one(
                f"""INSERT INTO public.tailored_cv_versions (
                       user_id, source_cv_id, target_role, company_name, jd_text,
                       tailored_cv, selected_design, analysis_key
                   )
                   VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8)
                   RETURNING {LEGACY_VERSION_COLUMNS}""",
                *legacy_args,
            )
    except Exception as exc:
        if getattr(exc, "sqlstate", None) == "23505":
            raise TailoredCVEntitlementUsedError from exc
        raise
    return _tailored_version(row)


async def list_versions(user_id: UUID) -> list[TailoredCVVersionResponse]:
    rows = await _fetch_version_rows(
        f"SELECT {VERSION_COLUMNS} FROM public.tailored_cv_versions WHERE user_id = $1 ORDER BY created_at DESC",
        f"SELECT {LEGACY_VERSION_COLUMNS} FROM public.tailored_cv_versions WHERE user_id = $1 ORDER BY created_at DESC",
        user_id,
    )
    return [_tailored_version(row) for row in rows]


async def get_version(version_id: UUID, user_id: UUID) -> TailoredCVVersionResponse:
    row = await _fetch_version_row(
        f"SELECT {VERSION_COLUMNS} FROM public.tailored_cv_versions WHERE id = $1 AND user_id = $2",
        f"SELECT {LEGACY_VERSION_COLUMNS} FROM public.tailored_cv_versions WHERE id = $1 AND user_id = $2",
        version_id,
        user_id,
    )
    if not row:
        raise TailoredCVNotFoundError
    return _tailored_version(row)


async def update_design(
    version_id: UUID, user_id: UUID, selected_design: CVDesign
) -> TailoredCVVersionResponse:
    row = await _fetch_version_row(
        f"""UPDATE public.tailored_cv_versions SET selected_design = $1, updated_at = now()
           WHERE id = $2 AND user_id = $3
           RETURNING {VERSION_COLUMNS}""",
        f"""UPDATE public.tailored_cv_versions SET selected_design = $1, updated_at = now()
           WHERE id = $2 AND user_id = $3
           RETURNING {LEGACY_VERSION_COLUMNS}""",
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
