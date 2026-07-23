from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response

from app.dependencies import get_current_user
from app.schemas.tailored_cv import (
    TailoredCVVersionCreate,
    TailoredCVVersionListResponse,
    TailoredCVVersionResponse,
    TailoredCVVersionUpdate,
)
from app.services import tailored_cv_service
from app.services.tailored_cv_pdf import generate_tailored_cv_pdf
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


@router.get("/{version_id}/pdf")
async def download_tailored_cv_pdf(
    version_id: str,
    user: dict = Depends(get_current_user),
) -> Response:
    try:
        version = await tailored_cv_service.get_version(
            _version_id(version_id),
            _user_id(user),
        )
    except TailoredCVNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy CV đã tối ưu hoặc bạn không có quyền truy cập.",
        )
    except UnsupportedCVSchemaVersionError as exc:
        raise _unsupported_schema(exc) from exc
    pdf = await generate_tailored_cv_pdf(
        tailored_cv=version.tailored_cv,
        design=version.selected_design,
        document_v2=version.document_v2,
        language=version.source_language,
    )
    filename = f"tailored-cv-{version.id}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch("/{version_id}", response_model=TailoredCVVersionResponse)
async def update_tailored_cv_design(
    version_id: str,
    req: TailoredCVVersionUpdate,
    user: dict = Depends(get_current_user),
) -> TailoredCVVersionResponse:
    try:
        return await tailored_cv_service.update_design(
            _version_id(version_id),
            _user_id(user),
            req.selected_design,
        )
    except TailoredCVNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy CV đã tối ưu hoặc bạn không có quyền truy cập.",
        )
    except UnsupportedCVSchemaVersionError as exc:
        raise _unsupported_schema(exc) from exc


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
