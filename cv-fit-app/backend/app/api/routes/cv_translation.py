"""Dedicated API route module for CV translation operations."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_current_user
from app.schemas.cv_translation import (
    CVTranslationListResponse,
    CVTranslationRequest,
    CVTranslationVariantResponse,
)
from app.services import cv_export_service
from app.services.cv_translation_validation import TranslationValidationError
from app.services.tailored_cv_service import (
    TailoredCVNotFoundError,
    UnsupportedCVSchemaVersionError,
)

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/user/tailored-cvs", tags=["cv-translation"])


def _version_id(val: str) -> UUID:
    try:
        return UUID(val)
    except (ValueError, AttributeError) as exc:
        raise HTTPException(status_code=400, detail="ID CV không hợp lệ.") from exc


def _user_id(user: dict) -> UUID:
    uid = user.get("id")
    if not uid:
        raise HTTPException(status_code=401, detail="Chưa xác thực người dùng.")
    try:
        return UUID(str(uid))
    except ValueError as exc:
        raise HTTPException(
            status_code=401, detail="ID người dùng không hợp lệ."
        ) from exc


def _unsupported_schema(exc: UnsupportedCVSchemaVersionError) -> HTTPException:
    return HTTPException(
        status_code=409,
        detail=f"Bản ghi CV sử dụng schema {exc.schema_version} không được hỗ trợ bởi phiên bản hiện tại.",
    )


@router.post("/{version_id}/translations", response_model=CVTranslationVariantResponse)
async def create_cv_translation(
    version_id: str,
    payload: CVTranslationRequest,
    user: dict = Depends(get_current_user),
) -> CVTranslationVariantResponse:
    """Create or retrieve a translated variant for a validated CV version."""
    ver_uuid = _version_id(version_id)
    u_uuid = _user_id(user)

    try:
        variant = await cv_export_service.create_translation(
            version_id=ver_uuid,
            user_id=u_uuid,
            target_language=payload.target_language,
        )
        return CVTranslationVariantResponse.model_validate(variant.model_dump())
    except TailoredCVNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy CV đã tối ưu hoặc bạn không có quyền truy cập.",
        )
    except UnsupportedCVSchemaVersionError as exc:
        raise _unsupported_schema(exc) from exc
    except TranslationValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        _logger.error("Dịch thuật CV thất bại: %s", exc)
        raise HTTPException(
            status_code=500, detail=f"Dịch thuật CV thất bại: {exc}"
        ) from exc


@router.get("/{version_id}/translations", response_model=CVTranslationListResponse)
async def list_cv_translations(
    version_id: str,
    user: dict = Depends(get_current_user),
) -> CVTranslationListResponse:
    """List all translation variants for a given CV version."""
    ver_uuid = _version_id(version_id)
    u_uuid = _user_id(user)

    try:
        variants = await cv_export_service.list_translations(
            version_id=ver_uuid,
            user_id=u_uuid,
        )
        return CVTranslationListResponse(
            translations=[
                CVTranslationVariantResponse.model_validate(v.model_dump())
                for v in variants
            ]
        )
    except TailoredCVNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy CV đã tối ưu hoặc bạn không có quyền truy cập.",
        )
    except Exception as exc:
        _logger.error("Lấy danh sách bản dịch thất bại: %s", exc)
        raise HTTPException(
            status_code=500, detail=f"Lấy danh sách bản dịch thất bại: {exc}"
        ) from exc
