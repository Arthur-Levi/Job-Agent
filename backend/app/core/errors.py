import logging
from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.request_context import REQUEST_ID_HEADER

logger = logging.getLogger(__name__)


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any | None = None
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


def error_payload(
    code: str, message: str, details: Any | None = None, request_id: str | None = None
) -> dict[str, Any]:
    return ErrorResponse(
        error=ErrorDetail(code=code, message=message, details=details, request_id=request_id)
    ).model_dump(mode="json")


class AppError(Exception):
    """Erro esperado da aplicação. Services levantam subclasses; o handler traduz para HTTP."""

    status_code: int = 500
    default_code: str = "INTERNAL_ERROR"
    default_message: str = "Internal server error"

    def __init__(
        self, message: str | None = None, *, code: str | None = None, details: Any | None = None
    ) -> None:
        self.message = message or self.default_message
        self.code = code or self.default_code
        self.details = details
        super().__init__(self.message)


class BadRequestError(AppError):
    status_code = 400
    default_code = "BAD_REQUEST"
    default_message = "Bad request"


class NotFoundError(AppError):
    status_code = 404
    default_code = "NOT_FOUND"
    default_message = "Resource not found"


class ConflictError(AppError):
    status_code = 409
    default_code = "CONFLICT"
    default_message = "Conflict with the current state of the resource"


class UnprocessableError(AppError):
    status_code = 422
    default_code = "UNPROCESSABLE"
    default_message = "Request is well-formed but violates a business rule"


class ServiceUnavailableError(AppError):
    status_code = 503
    default_code = "SERVICE_UNAVAILABLE"
    default_message = "Service temporarily unavailable"


def _respond(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: Any | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    request_id: str | None = getattr(request.state, "request_id", None)
    out_headers = dict(headers or {})
    if request_id:
        # Necessário no 500: o handler de Exception roda fora do RequestIdMiddleware.
        out_headers[REQUEST_ID_HEADER] = request_id
    return JSONResponse(
        status_code=status_code,
        content=error_payload(code, message, details, request_id),
        headers=out_headers or None,
    )


async def _handle_app_error(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, AppError):
        raise exc
    return _respond(request, exc.status_code, exc.code, exc.message, exc.details)


async def _handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        raise exc
    errors = exc.errors()
    if any(err["type"] == "json_invalid" for err in errors):
        return _respond(request, 400, "INVALID_JSON", "Request body is not valid JSON")
    # Só loc/msg/type: `input` e `ctx` poderiam ecoar dados do cliente ou não serializar.
    details = [
        {"loc": [str(part) for part in err["loc"]], "message": err["msg"], "type": err["type"]}
        for err in errors
    ]
    return _respond(request, 422, "VALIDATION_ERROR", "Request validation failed", details)


_HTTP_CODES = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}


async def _handle_http_exception(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):
        raise exc
    code = _HTTP_CODES.get(exc.status_code, f"HTTP_{exc.status_code}")
    message = exc.detail if isinstance(exc.detail, str) else "HTTP error"
    return _respond(request, exc.status_code, code, message, headers=exc.headers)


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    # Stack trace só no log; o cliente recebe mensagem genérica.
    logger.error(
        "unhandled exception",
        exc_info=exc,
        extra={"request_id": getattr(request.state, "request_id", None)},
    )
    return _respond(request, 500, "INTERNAL_ERROR", "Internal server error")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(Exception, _handle_unexpected_error)


def error_responses(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    """Documenta no OpenAPI os status de erro de uma rota (todos usam o envelope padrão)."""
    return {code: {"model": ErrorResponse} for code in status_codes}
