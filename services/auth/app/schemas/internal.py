from datetime import datetime

from pydantic import BaseModel

class Limits(BaseModel):
    max_watches: int
    check_interval_seconds: int
    allowed_channels: list[str]

class QuotaResponse(BaseModel):
    user_id: str
    plan: str
    limits: Limits
    valid_until: datetime | None = None

class VerifyTokenRequest(BaseModel):
    access_token: str

class VerifyTokenResponse(BaseModel):
    user_id: str
    role: str
    plan: str
    is_active: bool