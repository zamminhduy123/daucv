import json
import logging
from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID

from app.core.db import Database
from app.models.domain import TailoredCV
from app.schemas.tailored_cv import (
    CVDesign,
    TailoredCVVersionCreate,
    TailoredCVVersionResponse,
)
from app.services.block_reconstruction import _block_text_values
from app.services.cv_language import detect_tailored_cv_language
from app.services.cv_quality_checks import (
    build_source_preserving_tailored_cv_from_parts,
)
from app.services.cv_reconstruction_service import (
    normalize_cv_text,
    reconstruct_cv_text,
)
from app.services.cv_rendering_diagnostics import compact_rendering_warnings
from app.services.cv_tailoring_service import validate_tailored_document
from app.services.cv_v1_adapter import v1_to_v2_safe
from app.services.tailored_cv_metadata import (
    extract_target_metadata,
    verify_tailoring_entitlement,
)

VERSION_COLUMNS = "id, source_cv_id, target_role, company_name, jd_text, tailored_cv, document_v2, source_document_v2, source_pdf_reference, source_raw_text, source_normalized_text, selected_design, document_schema_version, reconstruction_version, source_hash, jd_hash, reconstruction_warnings, created_at, updated_at"
LEGACY_VERSION_COLUMNS = "id, source_cv_id, target_role, company_name, jd_text, tailored_cv, selected_design, created_at, updated_at"
V2_PERSISTENCE_COLUMNS = (
    "document_v2",
    "document_schema_version",
    "reconstruction_version",
    "source_hash",
    "jd_hash",
    "reconstruction_warnings",
    "source_document_v2",
    "source_pdf_reference",
    "source_raw_text",
    "source_normalized_text",
)

logger = logging.getLogger(__name__)


class TailoredCVNotFoundError(Exception):
    pass


class TailoredCVEntitlementError(Exception):
    pass


class TailoredCVEntitlementUsedError(Exception):
    pass


class CVPersistenceMigrationRequiredError(RuntimeError):
    pass


class UnsupportedCVSchemaVersionError(ValueError):
    def __init__(self, schema_version: int) -> None:
        self.schema_version = schema_version
        super().__init__(f"Unsupported CV document schema version: {schema_version}")


@dataclass(frozen=True)
class TailoredCVPersistenceRecord:
    """Typed boundary between version assembly and the database insert."""

    user_id: UUID
    source_cv_id: UUID | None
    target_role: str | None
    company_name: str | None
    jd_text: str
    tailored_cv_json: str
    selected_design: CVDesign
    analysis_key: str
    document_v2_json: str
    document_schema_version: int
    reconstruction_version: int
    source_hash: str | None
    jd_hash: str | None
    reconstruction_warnings: list[str]
    source_document_v2_json: str
    source_pdf_reference: str | None
    source_raw_text: str
    source_normalized_text: str

    def database_args(self) -> tuple[object, ...]:
        return (
            self.user_id,
            self.source_cv_id,
            self.target_role,
            self.company_name,
            self.jd_text,
            self.tailored_cv_json,
            self.selected_design,
            self.analysis_key,
            self.document_v2_json,
            self.document_schema_version,
            self.reconstruction_version,
            self.source_hash,
            self.jd_hash,
            self.reconstruction_warnings,
            self.source_document_v2_json,
            self.source_pdf_reference,
            self.source_raw_text,
            self.source_normalized_text,
        )


def _v2_persistence_columns_missing(exc: Exception) -> bool:
    """Detect a database missing the V2 persistence migrations."""
    message = str(exc).lower()
    return getattr(exc, "sqlstate", None) == "42703" and any(
        column in message for column in V2_PERSISTENCE_COLUMNS
    )


async def _fetch_version_row(
    query: str,
    legacy_query: str,
    *args: object,
) -> dict | None:
    try:
        return await Database.fetch_one(query, *args)
    except Exception as exc:
        if not _v2_persistence_columns_missing(exc):
            raise
        logger.warning(
            "CV document V2 columns are unavailable; using temporary V1 compatibility path",
        )
        return await Database.fetch_one(legacy_query, *args)


async def _fetch_version_rows(
    query: str,
    legacy_query: str,
    *args: object,
) -> list[dict]:
    try:
        return await Database.fetch_all(query, *args)
    except Exception as exc:
        if not _v2_persistence_columns_missing(exc):
            raise
        logger.warning(
            "CV document V2 columns are unavailable; using temporary V1 compatibility path",
        )
        return await Database.fetch_all(legacy_query, *args)


def _tailored_version(row: dict) -> TailoredCVVersionResponse:
    data = dict(row)
    tailored_cv_data = data.pop("tailored_cv", None)
    document_v2_data = data.pop("document_v2", None)
    source_document_v2_data = data.pop("source_document_v2", None)
    schema_version = data.pop("document_schema_version", 1)
    if isinstance(tailored_cv_data, str):
        tailored_cv_data = json.loads(tailored_cv_data)
    if isinstance(document_v2_data, str):
        document_v2_data = json.loads(document_v2_data)
    if isinstance(source_document_v2_data, str):
        source_document_v2_data = json.loads(source_document_v2_data)
    if tailored_cv_data:
        data["source_language"] = detect_tailored_cv_language(
            TailoredCV.model_validate(tailored_cv_data),
        )
    return normalize_version(
        tailored_cv_data=tailored_cv_data,
        document_v2_data=document_v2_data,
        source_document_v2=source_document_v2_data,
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
        },
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
    user_id: UUID,
    request: TailoredCVVersionCreate,
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
        "SELECT id, cv_filename FROM public.user_cvs WHERE user_id = $1 AND cv_text = $2 ORDER BY is_active DESC, created_at DESC LIMIT 1",
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

    from app.services.cv_reconstruction_service import canonical_cv_hash

    source_hash = (
        canonical_cv_hash(request.source_cv_text) if request.source_cv_text else None
    )
    jd_hash = (
        sha256(request.jd_text.encode("utf-8")).hexdigest() if request.jd_text else None
    )

    server_source_document = reconstruct_cv_text(request.source_cv_text)
    if request.source_document_v2 is not None:
        client_doc = request.source_document_v2
        client_blocks = [b for s in client_doc.sections for b in s.blocks]
        server_blocks = [b for s in server_source_document.sections for b in s.blocks]
        is_exact_content_match = len(client_blocks) == len(server_blocks) and all(
            _block_text_values(cb) == _block_text_values(sb)
            for cb, sb in zip(client_blocks, server_blocks, strict=True)
        )
        is_hash_match = client_doc.source_hash is not None and (
            client_doc.source_hash == source_hash
            or client_doc.source_hash == server_source_document.source_hash
        )

        if is_exact_content_match or (is_hash_match and is_exact_content_match):
            source_document = request.source_document_v2
            reconstruction_warnings = list(source_document.reconstruction_warnings)
        else:
            source_document = server_source_document
            reconstruction_warnings = list(source_document.reconstruction_warnings)
            reconstruction_warnings.append("client_source_document_ignored")
    else:
        source_document = server_source_document
        reconstruction_warnings = list(source_document.reconstruction_warnings)

    from app.services.cv_reconstruction_service import validate_reconstruction_gate

    validate_reconstruction_gate(source_document)
    if request.document_v2 is not None:
        tailored_document, validation_warnings = validate_tailored_document(
            source_document,
            request.document_v2,
            request.source_cv_text,
        )
        reconstruction_warnings.extend(validation_warnings)
    else:
        tailored_document = source_document.model_copy(deep=True)
    if request.document_v2 is None:
        reconstruction_warnings.append("tailored_document_fell_back_to_source")
    if request.selected_design == "compact_one_page":
        reconstruction_warnings.extend(compact_rendering_warnings(tailored_document))
    tailored_document.reconstruction_warnings = list(
        dict.fromkeys(
            [*tailored_document.reconstruction_warnings, *reconstruction_warnings],
        ),
    )
    reconstruction_warnings = tailored_document.reconstruction_warnings
    record = TailoredCVPersistenceRecord(
        user_id=user_id,
        source_cv_id=source["id"] if source else None,
        target_role=request.target_role or inferred_role,
        company_name=request.company_name or inferred_company,
        jd_text=request.jd_text,
        tailored_cv_json=json.dumps(complete_cv.model_dump()),
        selected_design=request.selected_design,
        analysis_key=analysis_key,
        document_v2_json=json.dumps(tailored_document.model_dump()),
        document_schema_version=2,
        reconstruction_version=tailored_document.reconstruction_version,
        source_hash=source_hash,
        jd_hash=jd_hash,
        reconstruction_warnings=reconstruction_warnings,
        source_document_v2_json=json.dumps(source_document.model_dump()),
        source_pdf_reference=source.get("cv_filename") if source else None,
        source_raw_text=request.source_cv_text,
        source_normalized_text=normalize_cv_text(request.source_cv_text),
    )
    try:
        row = await _insert_version_record(record)
    except Exception as exc:
        if getattr(exc, "sqlstate", None) == "23505":
            raise TailoredCVEntitlementUsedError from exc
        if _v2_persistence_columns_missing(exc):
            raise CVPersistenceMigrationRequiredError(
                "Database migrations 003 and 004 are required before saving V2 CVs",
            ) from exc
        raise
    return _tailored_version(row)


async def _insert_version_record(record: TailoredCVPersistenceRecord) -> dict:
    row = await Database.fetch_one(
        f"""INSERT INTO public.tailored_cv_versions (
               user_id, source_cv_id, target_role, company_name, jd_text,
               tailored_cv, selected_design, analysis_key,
               document_v2, document_schema_version, reconstruction_version,
               source_hash, jd_hash, reconstruction_warnings,
               source_document_v2, source_pdf_reference, source_raw_text,
               source_normalized_text
           )
           VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, $9::jsonb, $10, $11, $12, $13, $14, $15::jsonb, $16, $17, $18)
           RETURNING {VERSION_COLUMNS}""",
        *record.database_args(),
    )
    if row is None:
        raise RuntimeError("Tailored CV insert returned no row")
    return dict(row)


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
    version_id: UUID,
    user_id: UUID,
    selected_design: CVDesign,
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
