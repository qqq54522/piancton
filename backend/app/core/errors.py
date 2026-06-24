from __future__ import annotations

from typing import Any


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        details: Any | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


class NotFoundError(AppError):
    def __init__(self, code: str, message: str):
        super().__init__(code, message, status_code=404)


class ConflictError(AppError):
    def __init__(self, code: str, message: str):
        super().__init__(code, message, status_code=409)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "请先登录"):
        super().__init__("unauthorized", message, status_code=401)


class ForbiddenError(AppError):
    def __init__(self, message: str = "没有权限执行此操作"):
        super().__init__("forbidden", message, status_code=403)
