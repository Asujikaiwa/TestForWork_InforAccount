"""Application errors and the single JSON error envelope.

Every error response looks like:
    {"error": {"code": "SHARES_MISMATCH", "message": "...", "details": {...}}}
Clients branch on `code`; `message` is for humans and may change.
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    status_code = 400
    code = "BAD_REQUEST"

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class MissingUser(AppError):
    status_code, code = 401, "MISSING_USER"


class UnknownUser(AppError):
    status_code, code = 401, "UNKNOWN_USER"


class GroupNotFound(AppError):
    # Also used when the group exists but the user is not a member (see README).
    status_code, code = 404, "GROUP_NOT_FOUND"


class ExpenseNotFound(AppError):
    status_code, code = 404, "EXPENSE_NOT_FOUND"


class NotPayer(AppError):
    status_code, code = 403, "NOT_PAYER"


class IdempotencyKeyReused(AppError):
    status_code, code = 409, "IDEMPOTENCY_KEY_REUSED"


class InvalidAmount(AppError):
    status_code, code = 422, "INVALID_AMOUNT"


class AmountPrecision(AppError):
    status_code, code = 422, "AMOUNT_PRECISION"


class SharesMismatch(AppError):
    status_code, code = 422, "SHARES_MISMATCH"


class MemberNotInGroup(AppError):
    status_code, code = 422, "MEMBER_NOT_IN_GROUP"


class EmptySplit(AppError):
    status_code, code = 422, "EMPTY_SPLIT"


class InvalidRequest(AppError):
    status_code, code = 422, "VALIDATION_ERROR"


def error_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [
            {
                "field": ".".join(str(part) for part in err["loc"] if part != "body"),
                "message": err["msg"],
            }
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=error_body(
                "VALIDATION_ERROR", "The request body is invalid.", {"fields": fields}
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(
            exc.status_code, f"HTTP_{exc.status_code}"
        )
        return JSONResponse(status_code=exc.status_code, content=error_body(code, str(exc.detail)))

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, __: Exception) -> JSONResponse:
        # Never leak internals (SQL, stack traces) to the client.
        return JSONResponse(
            status_code=500, content=error_body("INTERNAL_ERROR", "Unexpected server error.")
        )
