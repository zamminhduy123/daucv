from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response

from app.dependencies import get_current_user
from app.models.cv_template import CVTemplateDefinition
from app.schemas.tailored_cv import (
    CVPreviewResponse,
    TailoredCVTemplateUpdateRequest,
    TailoredCVVersionCreate,
    TailoredCVVersionListResponse,
    TailoredCVVersionResponse,
    TailoredCVVersionUpdate,
)
from app.services import cv_export_service, tailored_cv_service
from app.services.cv_template_registry import list_templates
from app.services.tailored_cv_service import (
    CVPersistenceMigrationRequiredError,
    TailoredCVEntitlementError,
    TailoredCVEntitlementUsedError,
    TailoredCVNotFoundError,
    UnsupportedCVSchemaVersionError,
)

router = APIRouter(prefix="/api/user/tailored-cvs", tags=["tailored-cv"])


def _version_id(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="ID CV không hợp lệ.") from exc


def _user_id(user: dict) -> UUID:
    return UUID(str(user["id"]))


@router.get("/templates", response_model=list[CVTemplateDefinition])
async def list_cv_templates(
    user: dict = Depends(get_current_user),
) -> list[CVTemplateDefinition]:
    """Return list of all registered server-owned templates."""
    return list_templates()


@router.get("", response_model=TailoredCVVersionListResponse)
async def list_tailored_cvs(
    user: dict = Depends(get_current_user),
) -> TailoredCVVersionListResponse:
    try:
        return TailoredCVVersionListResponse(
            versions=await tailored_cv_service.list_versions(_user_id(user)),
        )
    except UnsupportedCVSchemaVersionError as exc:
        raise _unsupported_schema(exc) from exc


@router.post("", response_model=TailoredCVVersionResponse)
async def create_tailored_cv_version(
    req: TailoredCVVersionCreate,
    user: dict = Depends(get_current_user),
) -> TailoredCVVersionResponse:
    try:
        return await tailored_cv_service.create_version(_user_id(user), req)
    except TailoredCVEntitlementError:
        raise HTTPException(
            status_code=403,
            detail="Lượt tạo CV không hợp lệ. Vui lòng phân tích CV lại.",
        )
    except TailoredCVEntitlementUsedError:
        raise HTTPException(
            status_code=409,
            detail="CV đã tối ưu của lượt phân tích này đã được tạo.",
        )
    except CVPersistenceMigrationRequiredError:
        raise HTTPException(
            status_code=503,
            detail="Hệ thống lưu CV đang được nâng cấp. Vui lòng thử lại sau.",
        )
    except UnsupportedCVSchemaVersionError as exc:
        raise _unsupported_schema(exc) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.get("/{version_id}/preview", response_model=CVPreviewResponse)
async def preview_tailored_cv(
    version_id: str,
    translation_variant_id: str | None = None,
    user: dict = Depends(get_current_user),
) -> CVPreviewResponse:
    """Return canonical server-rendered HTML preview payload."""
    try:
        variant_uuid = (
            _version_id(translation_variant_id) if translation_variant_id else None
        )
        return await cv_export_service.get_preview(
            _version_id(version_id),
            _user_id(user),
            translation_variant_id=variant_uuid,
        )
    except TailoredCVNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy CV đã tối ưu hoặc bạn không có quyền truy cập.",
        )
    except UnsupportedCVSchemaVersionError as exc:
        raise _unsupported_schema(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{version_id}/pdf")
async def download_tailored_cv_pdf(
    version_id: str,
    translation_variant_id: str | None = None,
    user: dict = Depends(get_current_user),
) -> Response:
    """Download PDF for original or translated CV version."""
    ver_uuid = _version_id(version_id)
    try:
        variant_uuid = (
            _version_id(translation_variant_id) if translation_variant_id else None
        )
        pdf = await cv_export_service.generate_pdf(
            ver_uuid,
            _user_id(user),
            translation_variant_id=variant_uuid,
        )
    except TailoredCVNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy CV đã tối ưu hoặc bạn không có quyền truy cập.",
        )
    except UnsupportedCVSchemaVersionError as exc:
        raise _unsupported_schema(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Tạo file PDF thất bại: {exc}",
        ) from exc

    filename = f"tailored-cv-{version_id}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch("/{version_id}/template", response_model=TailoredCVVersionResponse)
async def update_tailored_cv_template(
    version_id: str,
    req: TailoredCVTemplateUpdateRequest,
    user: dict = Depends(get_current_user),
) -> TailoredCVVersionResponse:
    """Update selected template ID; server resolves and pins template version."""
    try:
        return await tailored_cv_service.update_template(
            _version_id(version_id),
            _user_id(user),
            req.template_id,
        )
    except TailoredCVNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy CV đã tối ưu hoặc bạn không có quyền truy cập.",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/{version_id}", response_model=TailoredCVVersionResponse)
async def update_tailored_cv_design(
    version_id: str,
    req: TailoredCVVersionUpdate,
    user: dict = Depends(get_current_user),
) -> TailoredCVVersionResponse:
    target_design = req.template_id or req.selected_design
    if not target_design:
        raise HTTPException(
            status_code=400, detail="Cần chọn template_id hoặc selected_design."
        )
    try:
        return await tailored_cv_service.update_template(
            _version_id(version_id),
            _user_id(user),
            target_design,
        )
    except TailoredCVNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy CV đã tối ưu hoặc bạn không có quyền truy cập.",
        )
    except UnsupportedCVSchemaVersionError as exc:
        raise _unsupported_schema(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{version_id}")
async def delete_tailored_cv_version(
    version_id: str,
    user: dict = Depends(get_current_user),
) -> dict:
    try:
        await tailored_cv_service.delete_version(
            _version_id(version_id),
            _user_id(user),
        )
        return {"success": True}
    except TailoredCVNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy CV đã tối ưu hoặc bạn không có quyền truy cập.",
        )


def _unsupported_schema(exc: UnsupportedCVSchemaVersionError) -> HTTPException:
    return HTTPException(
        status_code=409,
        detail=(
            "Phiên bản dữ liệu CV này chưa được hỗ trợ. "
            f"Vui lòng cập nhật ứng dụng (schema {exc.schema_version})."
        ),
    )
