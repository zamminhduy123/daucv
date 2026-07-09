from pydantic import BaseModel, Field


class FeedbackSubmit(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Đánh giá từ 1 đến 5 sao")
    content: str = Field(..., min_length=5, description="Nội dung ý kiến đóng góp")


class FeedbackResponse(BaseModel):
    success: bool
    message: str
    credits_rewarded: int
    new_credits: int
