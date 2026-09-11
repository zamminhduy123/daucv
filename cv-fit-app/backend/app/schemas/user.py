from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.cv_document_v2 import CVDocumentV2


class CVResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cv_filename: str
    cv_text: str
    is_active: bool
    created_at: datetime
    raw_extraction_ref: str | None = None
    pdf_file_id: str | None = None
    pdf_url: str | None = None
    thumbnail_file_id: str | None = None


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    name: str | None = None
    image: str | None = None
    credits: int
    active_cv: CVResponse | None = None
    total_cvs: int = 0
    active_cv_age_days: int | None = None


class UpdateCVRequest(BaseModel):
    cv_text: str = Field(..., min_length=1, description="Nội dung plain text của CV")
    cv_filename: str = Field(..., min_length=1, description="Tên file CV gốc")
    raw_extraction_ref: str | None = Field(
        default=None,
        description="Raw extraction file id giữ layout để chọn lại CV vẫn parse chính xác",
    )
    pdf_file_id: str | None = Field(
        default=None,
        description="Uploaded source PDF file id để render thumbnail trang đầu",
    )
    thumbnail_file_id: str | None = Field(
        default=None,
        description="Pre-rendered first-page JPEG thumbnail file id",
    )


class CVListResponse(BaseModel):
    cvs: list[CVResponse]


class StructuredDocumentSaveRequest(BaseModel):
    document: CVDocumentV2
