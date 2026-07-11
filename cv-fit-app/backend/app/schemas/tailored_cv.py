from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.domain import SuggestedEdit, TailoredCV

CVDesign = Literal["classic_ats", "modern_professional", "compact_one_page"]


class TailoredCVVersionCreate(BaseModel):
    tailored_cv: TailoredCV
    source_cv_text: str = Field(..., min_length=1)
    suggested_edits: list[SuggestedEdit] = Field(default_factory=list)
    jd_text: str = ""
    target_role: str | None = None
    company_name: str | None = None
    selected_design: CVDesign = "classic_ats"


class TailoredCVVersionUpdate(BaseModel):
    selected_design: CVDesign


class TailoredCVVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_cv_id: UUID | None = None
    target_role: str | None = None
    company_name: str | None = None
    jd_text: str
    tailored_cv: TailoredCV
    selected_design: CVDesign
    created_at: datetime
    updated_at: datetime


class TailoredCVVersionListResponse(BaseModel):
    versions: list[TailoredCVVersionResponse]
