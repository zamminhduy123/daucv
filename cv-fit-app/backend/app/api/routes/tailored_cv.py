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
    return TailoredCVVersionListResponse(
        versions=await tailored_cv_service.list_versions(_user_id(user))
    )


@router.post("", response_model=TailoredCVVersionResponse)
async def create_tailored_cv_version(
    req: TailoredCVVersionCreate, user: dict = Depends(get_current_user)
) -> TailoredCVVersionResponse:
    return await tailored_cv_service.create_version(_user_id(user), req)


@router.get("/{version_id}/pdf")
async def download_tailored_cv_pdf(
    version_id: str, user: dict = Depends(get_current_user)
) -> Response:
    version = await tailored_cv_service.get_version(
        _version_id(version_id), _user_id(user)
    )
    pdf = await generate_tailored_cv_pdf(version.tailored_cv, version.selected_design)
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
    return await tailored_cv_service.update_design(
        _version_id(version_id), _user_id(user), req.selected_design
    )


@router.delete("/{version_id}")
async def delete_tailored_cv_version(
    version_id: str, user: dict = Depends(get_current_user)
) -> dict:
    await tailored_cv_service.delete_version(_version_id(version_id), _user_id(user))
    return {"success": True}
