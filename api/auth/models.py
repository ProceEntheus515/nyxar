"""Modelos Pydantic para autenticación NYXAR (S01)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from api.auth.roles import ROLE_HIERARCHY


class User(BaseModel):
    id: str
    username: str
    role: str
    area: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    last_login: Optional[datetime] = None


class TokenData(BaseModel):
    username: str
    role: str
    exp: Optional[int] = None


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=200)
    password: str = Field(..., min_length=1, max_length=500)


class CreateApiKeyBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    role: str = Field(..., min_length=1, max_length=32)

    @field_validator("role")
    @classmethod
    def role_must_be_known(cls, v: str) -> str:
        s = v.strip().lower()
        if s not in ROLE_HIERARCHY:
            raise ValueError(f"Rol no válido: {v}")
        return s
