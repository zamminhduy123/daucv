import json
import logging
from dataclasses import dataclass
from hashlib import sha256
from typing import Any
from uuid import UUID

from app.core.db import Database
from app.models.cv_document_v2 import (
    CURRENT_RECONSTRUCTION_VERSION,
    CVDocumentV2,
)
from app.models.cv_template import CURRENT_RENDER_VERSION
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
from app.services.cv_reconstruction_service import (
    normalize_cv_text,
    reconstruct_cv_text,
)
from app.services.cv_rendering_diagnostics import compact_rendering_warnings
from app.services.cv_tailoring_service import (
    validate_tailored_document,
    validate_tailored_document_gate,
)
from app.services.cv_template_registry import (
    get_template_definition,
    resolve_template_id,
)
from app.services.cv_v1_adapter import v1_to_v2_safe
from app.services.tailored_cv_metadata import (
    extract_target_metadata,
    verify_tailoring_entitlement,
    verify_tailoring_entitlement_v2,
    verify_tailoring_entitlement_v3,
)

VERSION_COLUMNS = "id, source_cv_id, target_role, company_name, jd_text, tailored_cv, document_v2, source_document_v2, tailoring_diagnostics, template_id, template_version, render_version, last_render_diagnostics, source_pdf_reference, source_raw_text, source_normalized_text, selected_design, document_schema_version, reconstruction_version, source_hash, jd_hash, reconstruction_warnings, tailoring_pipeline_version, created_at, updated_at"
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
    "tailoring_diagnostics",
    "tailoring_pipeline_version",
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


def _legacy_source_document(
    source_text: str,
    *,
    client_source_was_ignored: bool,
) -> CVDocumentV2:
    """Build a renderable compatibility document that cannot appear current."""
    document = reconstruct_cv_text(source_text)
    document.reconstruction_version = max(1, CURRENT_RECONSTRUCTION_VERSION - 1)
    document.requires_reprocessing = True
    warnings = [
        *document.reconstruction_warnings,
        "legacy_source_requires_reprocessing",
    ]
    if client_source_was_ignored:
        warnings.append("legacy_entitlement_source_document_ignored")
    document.reconstruction_warnings = list(dict.fromkeys(warnings))
    return document


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
    tailoring_diagnostics_json: str | None = None
    template_id: str | None = None
    template_version: int | None = None
    render_version: int | None = None
    last_render_diagnostics_json: str | None = None
    tailoring_pipeline_version: int = 1

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
            self.tailoring_diagnostics_json,
            self.template_id,
            self.template_version,
            self.render_version,
            self.last_render_diagnostics_json,
            self.tailoring_pipeline_version,
        )


def _v2_persistence_columns_missing(exc: Exception) -> bool:
    """Detect a database missing the V2 persistence migrations."""
    if isinstance(exc, KeyError):
        return True
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
    tailoring_diagnostics_data = data.pop("tailoring_diagnostics", None)
    schema_version = data.pop("document_schema_version", 1)
    if isinstance(tailored_cv_data, str):
        tailored_cv_data = json.loads(tailored_cv_data)
    if isinstance(document_v2_data, str):
        document_v2_data = json.loads(document_v2_data)
    if isinstance(source_document_v2_data, str):
        source_document_v2_data = json.loads(source_document_v2_data)
    if isinstance(tailoring_diagnostics_data, str):
        tailoring_diagnostics_data = json.loads(tailoring_diagnostics_data)
    last_diagnostics = data.pop("last_render_diagnostics", None)
    if isinstance(last_diagnostics, str):
        last_diagnostics = json.loads(last_diagnostics)
    if tailored_cv_data:
        data["source_language"] = detect_tailored_cv_language(
            TailoredCV.model_validate(tailored_cv_data),
        )
    return normalize_version(
        tailored_cv_data=tailored_cv_data,
        document_v2_data=document_v2_data,
        source_document_v2=source_document_v2_data,
        tailoring_diagnostics=tailoring_diagnostics_data,
        schema_version=schema_version,
        last_render_diagnostics=last_diagnostics,
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
    from app.models.cv_document_v2 import CURRENT_RECONSTRUCTION_VERSION

    rec_version = getattr(response, "reconstruction_version", 1) or 1
    response.reconstruction_status = (
        "current" if rec_version >= CURRENT_RECONSTRUCTION_VERSION else "outdated"
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
    is_v3_entitlement = request.tailoring_entitlement.startswith("v3.")
    is_v2_entitlement = (
        request.tailoring_entitlement.startswith("v2.") or is_v3_entitlement
    )

    if is_v3_entitlement:
        if (
            request.source_document_v2 is None
            or request.document_v2 is None
            or request.tailoring_diagnostics is None
        ):
            raise TailoredCVEntitlementError(
                "V3 entitlement requires source, tailored document, and diagnostics",
            )
        try:
            analysis_key = verify_tailoring_entitlement_v3(
                request.tailoring_entitlement,
                user_id,
                request.source_cv_text,
                request.jd_text,
                request.source_document_v2,
                request.document_v2,
                request.tailoring_diagnostics,
            )
        except ValueError as exc:
            raise TailoredCVEntitlementError from exc
    elif is_v2_entitlement:
        if request.source_document_v2 is None:
            raise TailoredCVEntitlementError(
                "V2 entitlement requires source_document_v2"
            )
        try:
            analysis_key = verify_tailoring_entitlement_v2(
                request.tailoring_entitlement,
                user_id,
                request.source_cv_text,
                request.jd_text,
                request.source_document_v2,
            )
        except ValueError as exc:
            raise TailoredCVEntitlementError from exc
    else:
        # Legacy entitlement — cannot authorize a V2 source document
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

    if is_v2_entitlement:
        # V2: source document is hash-verified by the entitlement
        source_document = request.source_document_v2
        reconstruction_warnings = list(source_document.reconstruction_warnings)
    elif request.source_document_v2 is not None:
        # Legacy entitlement cannot authorize a client-supplied V2 source document
        source_document = _legacy_source_document(
            request.source_cv_text,
            client_source_was_ignored=True,
        )
        reconstruction_warnings = list(source_document.reconstruction_warnings)
    else:
        source_document = _legacy_source_document(
            request.source_cv_text,
            client_source_was_ignored=False,
        )
        reconstruction_warnings = list(source_document.reconstruction_warnings)

    from app.services.cv_reconstruction_service import validate_reconstruction_gate

    if is_v2_entitlement:
        validate_reconstruction_gate(source_document)
    if is_v3_entitlement:
        assert request.document_v2 is not None
        assert request.tailoring_diagnostics is not None
        try:
            validate_tailored_document_gate(
                source_document,
                request.document_v2,
                request.tailoring_diagnostics,
            )
        except ValueError as exc:
            raise TailoredCVEntitlementError from exc
        tailored_document = request.document_v2.model_copy(deep=True)
    elif request.document_v2 is not None:
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
    if request.selected_design == "compact_one_page" and not is_v3_entitlement:
        reconstruction_warnings.extend(compact_rendering_warnings(tailored_document))
    if not is_v3_entitlement:
        tailored_document.reconstruction_warnings = list(
            dict.fromkeys(
                [*tailored_document.reconstruction_warnings, *reconstruction_warnings],
            ),
        )
    reconstruction_warnings = tailored_document.reconstruction_warnings
    from app.services.cv_template_render_service import render_cv_document

    template_id = resolve_template_id(request.selected_design)
    template_def = get_template_definition(template_id)
    template_version = template_def.version
    render_version = CURRENT_RENDER_VERSION
    last_render_diagnostics_json = None

    if is_v3_entitlement:
        from app.services.cv_language import detect_cv_language

        lang = (
            detect_cv_language(request.source_cv_text)
            if request.source_cv_text
            else "vi"
        )
        render_res = render_cv_document(
            document=tailored_document,
            template_id=template_id,
            template_version=template_version,
            language=lang,
        )
        if not render_res.diagnostics.is_valid:
            logger.warning(
                "Rendering validation non-fatal warnings for tailored document: missing=%s, duplicate=%s, mismatched=%s",
                render_res.diagnostics.missing_field_ids,
                render_res.diagnostics.duplicate_field_ids,
                render_res.diagnostics.mismatched_field_ids,
            )
        last_render_diagnostics_json = json.dumps(render_res.diagnostics.model_dump())

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
        tailoring_diagnostics_json=(
            json.dumps(request.tailoring_diagnostics.model_dump())
            if is_v3_entitlement and request.tailoring_diagnostics is not None
            else None
        ),
        template_id=template_id,
        template_version=template_version,
        render_version=render_version,
        last_render_diagnostics_json=last_render_diagnostics_json,
        tailoring_pipeline_version=3 if is_v3_entitlement else 1,
    )
    try:
        row = await _insert_version_record(record)
    except Exception as exc:
        if getattr(exc, "sqlstate", None) == "23505":
            raise TailoredCVEntitlementUsedError from exc
        if _v2_persistence_columns_missing(exc):
            raise CVPersistenceMigrationRequiredError(
                "V2 document persistence columns missing. Apply database migrations 003, 004, and 006.",
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
                   source_normalized_text, tailoring_diagnostics,
                   template_id, template_version, render_version, last_render_diagnostics,
                   tailoring_pipeline_version
               )
               VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, $9::jsonb, $10, $11, $12, $13, $14, $15::jsonb, $16, $17, $18, $19::jsonb, $20, $21, $22, $23::jsonb, $24)
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
    return await update_template(version_id, user_id, selected_design)


async def update_template(
    version_id: UUID,
    user_id: UUID,
    template_id: str,
) -> TailoredCVVersionResponse:
    """Update selected template; server resolves template_id and pins template_version."""
    canonical_id = resolve_template_id(template_id)
    template_def = get_template_definition(canonical_id)

    # 1. Fetch current version to get document
    version = await get_version(version_id, user_id)
    document = version.document_v2 or v1_to_v2_safe(version.tailored_cv)
    if not document:
        raise ValueError("Cannot render CV version content.")

    # 2. Render new template to verify render validation passes and get diagnostics
    from app.services.cv_template_render_service import render_cv_document

    render_res = render_cv_document(
        document=document,
        template_id=canonical_id,
        template_version=template_def.version,
        language=version.source_language or "vi",
    )
    if not render_res.diagnostics.is_valid:
        logger.warning(
            "Rendering validation non-fatal warnings for tailored document: missing=%s, duplicate=%s, mismatched=%s",
            render_res.diagnostics.missing_field_ids,
            render_res.diagnostics.duplicate_field_ids,
            render_res.diagnostics.mismatched_field_ids,
        )

    last_render_diagnostics_json = json.dumps(render_res.diagnostics.model_dump())

    row = await _fetch_version_row(
        f"""UPDATE public.tailored_cv_versions
           SET template_id = $1, template_version = $2, render_version = $3, selected_design = $1, last_render_diagnostics = $6::jsonb, updated_at = now()
           WHERE id = $4 AND user_id = $5
           RETURNING {VERSION_COLUMNS}""",
        f"""UPDATE public.tailored_cv_versions
           SET selected_design = $1, updated_at = now()
           WHERE id = $2 AND user_id = $3
           RETURNING {LEGACY_VERSION_COLUMNS}""",
        canonical_id,
        template_def.version,
        CURRENT_RENDER_VERSION,
        version_id,
        user_id,
        last_render_diagnostics_json,
    )
    if not row:
        raise TailoredCVNotFoundError
    return _tailored_version(row)


def verify_exportable_v3_gates(version: Any) -> None:
    """Explicitly rerun Phase 5 reconstruction and tailoring gates before export/rendering."""
    pipeline_ver = getattr(version, "tailoring_pipeline_version", 1) or 1
    schema_version = getattr(version, "document_schema_version", 1) or 1
    doc_v2 = getattr(version, "document_v2", None)

    if pipeline_ver < 3 or schema_version < 2 or not doc_v2:
        raise ValueError(
            "Reprocess required: legacy record cannot enter V3 export pipeline."
        )

    status = getattr(version, "reconstruction_status", "current")
    if status == "outdated":
        raise ValueError(
            "This CV version is outdated and requires reprocessing before export."
        )

    src_doc_v2 = getattr(version, "source_document_v2", None)
    diagnostics = getattr(version, "tailoring_diagnostics", None)

    if schema_version >= 2:
        if not src_doc_v2:
            raise ValueError(
                "Source document (V2) is missing but required for V3 schema."
            )
        if not diagnostics:
            raise ValueError(
                "Tailoring diagnostics are missing but required for V3 schema."
            )

    from app.services.cv_reconstruction_service import validate_reconstruction_gate

    validate_reconstruction_gate(src_doc_v2)
    validate_tailored_document_gate(
        src_doc_v2,
        doc_v2,
        diagnostics,
    )


async def get_cv_preview(version_id: UUID, user_id: UUID) -> Any:
    """Preview orchestration moved to service layer.

    Performs gate validation, adaptation, and rendering.
    """
    version = await get_version(version_id, user_id)
    verify_exportable_v3_gates(version)

    document = version.document_v2 or v1_to_v2_safe(version.tailored_cv)
    if not document:
        raise ValueError("Cannot render CV version content.")

    target_template = version.template_id or version.selected_design or "classic_ats"

    from app.services.cv_template_render_service import render_cv_document

    render_result = render_cv_document(
        document=document,
        template_id=target_template,
        template_version=version.template_version,
        language=version.source_language or "vi",
    )

    from app.schemas.tailored_cv import CVPreviewResponse

    return CVPreviewResponse(
        html=render_result.html,
        diagnostics=render_result.diagnostics,
        render_hash=render_result.render_hash,
    )


async def delete_version(version_id: UUID, user_id: UUID) -> None:
    deleted = await Database.execute(
        "DELETE FROM public.tailored_cv_versions WHERE id = $1 AND user_id = $2",
        version_id,
        user_id,
    )
    if deleted == "DELETE 0":
        raise TailoredCVNotFoundError
