"""Application error types and their HTTP mappings."""

from __future__ import annotations

from typing import Any


class ApiError(Exception):
    """Base class for expected API failures."""

    status_code = 400
    code = "error"

    def __init__(self, detail: str, *, code: str | None = None, extra: Any = None):
        super().__init__(detail)
        self.detail = detail
        if code:
            self.code = code
        self.extra = extra


class ValidationError(ApiError):
    status_code = 400
    code = "validation_error"


class AuthError(ApiError):
    status_code = 401
    code = "auth_error"


class NotFoundError(ApiError):
    status_code = 404
    code = "not_found"


class ForbiddenError(ApiError):
    status_code = 403
    code = "forbidden"


class ConflictError(ApiError):
    status_code = 409
    code = "conflict"


class BadGatewayError(ApiError):
    """An upstream provider (STT/TTS/web search) failed or is unconfigured."""
    status_code = 502
    code = "bad_gateway"
