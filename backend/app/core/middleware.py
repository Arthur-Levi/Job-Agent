import logging
import re
import time
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings
from app.db.session import Database
from app.services.auth_rate_limit import consume, RateLimitExceeded, RateLimitUnavailable
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import error_payload
from app.core.request_context import (
    REQUEST_ID_HEADER,
    reset_request_id,
    set_request_id,
)

logger = logging.getLogger("app.request")

# Aceita IDs fornecidos pelo cliente apenas se forem "seguros" para log e header.
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")


class RequestIdMiddleware:
    """Correlação por request + log de acesso (sem query string, que pode ter dados sensíveis)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = Headers(scope=scope).get(REQUEST_ID_HEADER)
        request_id = incoming if incoming and _VALID_REQUEST_ID.fullmatch(incoming) else uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        token = set_request_id(request_id)
        started = time.perf_counter()
        status_code = 500

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            logger.info(
                "request completed",
                extra={
                    "method": scope["method"],
                    "path": scope["path"],
                    "status_code": status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )
            reset_request_id(token)


class BodySizeLimitMiddleware:
    """Rejeita requests cujo Content-Length declarado excede o limite.

    Limitação conhecida: corpos chunked (sem Content-Length) não são limitados aqui.
    """

    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            raw = Headers(scope=scope).get("content-length")
            if raw is not None:
                request_id = scope.get("state", {}).get("request_id")
                try:
                    size = int(raw)
                except ValueError:
                    size = -1
                if size < 0:
                    response = JSONResponse(
                        error_payload("BAD_REQUEST", "Invalid Content-Length", None, request_id),
                        status_code=400,
                    )
                    await response(scope, receive, send)
                    return
                if size > self.max_bytes:
                    response = JSONResponse(
                        error_payload(
                            "PAYLOAD_TOO_LARGE",
                            f"Request body exceeds {self.max_bytes} bytes",
                            None,
                            request_id,
                        ),
                        status_code=413,
                    )
                    await response(scope, receive, send)
                    return
        await self.app(scope, receive, send)


class AuthRateLimitMiddleware:
    """Throttle auth POSTs before Pydantic parsing, including malformed bodies.

    Reads only ASGI client peer address. Trust proxy headers exclusively through
    Uvicorn's explicit --forwarded-allow-ips, never directly here.
    """

    def __init__(self, app: ASGIApp, *, database: Database, settings: Settings) -> None:
        self.app = app
        self.database = database
        self.settings = settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self.settings.auth_rate_limit_enabled or scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path")
        if scope.get("method") != "POST" or path not in (
            "/api/v1/auth/login", "/api/v1/auth/register",
        ):
            await self.app(scope, receive, send)
            return

        peer = scope.get("client")
        identity = peer[0] if peer and peer[0] else "unknown"
        kind = "login_ip" if path == "/api/v1/auth/login" else "register_ip"
        maximum = (
            self.settings.auth_login_ip_max
            if kind == "login_ip" else self.settings.auth_register_ip_max
        )
        try:
            await run_in_threadpool(
                consume, self.database, self.settings,
                kind=kind, identity=identity, maximum=maximum,
            )
        except RateLimitExceeded as exc:
            response = JSONResponse(
                error_payload("RATE_LIMITED", "Too many requests. Try again later."),
                status_code=429,
                headers={"Retry-After": str(exc.retry_after)},
            )
            await response(scope, receive, send)
            return
        except RateLimitUnavailable:
            response = JSONResponse(
                error_payload("AUTH_PROTECTION_UNAVAILABLE", "Service temporarily unavailable"),
                status_code=503,
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)
