from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

from app.schemas.base import ApiModel

Role = Literal["business", "designer", "admin"]
AvatarPreset = Literal["blue", "mint", "coral", "violet", "gold", "slate"]


class LoginRequest(ApiModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=200)


class RegisterRequest(ApiModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=200)
    confirm_password: str = Field(min_length=8, max_length=200)
    avatar_preset_id: AvatarPreset | None = None

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


class AvatarPresetRequest(ApiModel):
    preset_id: AvatarPreset


class UserRead(ApiModel):
    id: str
    username: str
    role: Role
    is_active: bool
    onboarding_completed_at: datetime | None
    avatar_preset_id: AvatarPreset | None = None
    avatar_updated_at: datetime | None = None
    has_custom_avatar: bool = False
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def expose_avatar_state(cls, value):
        if isinstance(value, dict):
            return value
        if hasattr(value, "avatar_storage_key"):
            return {
                "id": value.id,
                "username": value.username,
                "role": value.role,
                "is_active": value.is_active,
                "onboarding_completed_at": value.onboarding_completed_at,
                "avatar_preset_id": value.avatar_preset_id,
                "avatar_updated_at": value.avatar_updated_at,
                "has_custom_avatar": bool(value.avatar_storage_key),
                "created_at": value.created_at,
            }
        return value


class LoginResponse(ApiModel):
    user: UserRead
    csrf_token: str


class UserCreate(ApiModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=200)
    role: Role
    avatar_preset_id: AvatarPreset | None = None


class UserUpdate(ApiModel):
    role: Role | None = None
    is_active: bool | None = None


class PasswordReset(ApiModel):
    password: str = Field(min_length=8, max_length=200)
