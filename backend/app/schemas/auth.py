from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

from app.schemas.base import ApiModel

Role = Literal["business", "designer", "admin"]


class LoginRequest(ApiModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=200)


class RegisterRequest(ApiModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=200)
    confirm_password: str = Field(min_length=8, max_length=200)

    @field_validator("username", mode="before")
    @classmethod
    def trim_username(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def check_passwords(self):
        if not self.password.strip():
            raise PydanticCustomError("blank_password", "密码不能全部为空格")
        if self.password != self.confirm_password:
            raise PydanticCustomError("password_mismatch", "两次输入的密码不一致")
        return self


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
