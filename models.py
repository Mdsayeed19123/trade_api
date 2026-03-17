"""Pydantic response models."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    message: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_at: str
    session_id: str
