from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

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
    name: Optional[str] = None
    image: Optional[str] = None
    credits: int
    active_cv: Optional[CVResponse] = None
    total_cvs: int = 0
    active_cv_age_days: Optional[int] = None

class UpdateCVRequest(BaseModel):
    cv_text: str = Field(..., min_length=1, description="Nội dung plain text của CV")
    cv_filename: str = Field(..., min_length=1, description="Tên file CV gốc")

class CVListResponse(BaseModel):
    cvs: List[CVResponse]
