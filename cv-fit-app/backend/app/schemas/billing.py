from pydantic import BaseModel


class BuyCreditsRequest(BaseModel):
    package_id: str  # "starter" | "pro" | "premium"


class BuyCreditsResponse(BaseModel):
    checkout_url: str


class MockPaymentConfirmRequest(BaseModel):
    package_id: str
    amount: int
    credits_to_add: int


class MockPaymentConfirmResponse(BaseModel):
    success: bool
    new_credits: int
