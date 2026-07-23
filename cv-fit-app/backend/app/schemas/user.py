from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CVResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cv_filename: str
    cv_text: str
    is_active: bool
    created_at: datetime


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


class CVListResponse(BaseModel):
    cvs: list[CVResponse]
