from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.base import ApiModel

Role = Literal["business", "designer", "admin"]


class LoginRequest(ApiModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=200)


class UserRead(ApiModel):
    id: str
    username: str
    role: Role
    is_active: bool
    created_at: datetime


class LoginResponse(ApiModel):
    user: UserRead
    csrf_token: str


class UserCreate(ApiModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=200)
    role: Role


class UserUpdate(ApiModel):
    role: Role | None = None
    is_active: bool | None = None


class PasswordReset(ApiModel):
    password: str = Field(min_length=8, max_length=200)
