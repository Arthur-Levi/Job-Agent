"""D2-E1.5 trusted proxy policy tests: no DB, no network.

Uvicorn changes ASGI scope client only if connecting peer is trusted.
The application MUST still be inaccessible directly from the public internet.
"""
from collections.abc import Awaitable, Callable
from typing import Any

from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware


def test_proxy_headers_only_from_trusted_peer() -> None:
    import asyncio

    async def exercise(peer: str) -> tuple[str, int]:
        seen: list[tuple[str, int]] = []

        async def inner(
            scope: dict[str, Any],
            receive: Callable[[], Awaitable[dict[str, Any]]],
            send: Callable[[dict[str, Any]], Awaitable[None]],
        ) -> None:
            seen.append(scope["client"])

        app = ProxyHeadersMiddleware(inner, trusted_hosts=["127.0.0.1"])
        scope: dict[str, Any] = {
            "type": "http", "method": "GET", "path": "/",
            "scheme": "http",
            "headers": [(b"x-forwarded-for", b"203.0.113.19")],
            "client": (peer, 54321),
            "server": ("127.0.0.1", 18081),
        }

        async def receive() -> dict[str, Any]:
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict[str, Any]) -> None:
            return None

        await app(scope, receive, send)
        assert len(seen) == 1
        return seen[0]

    assert asyncio.run(exercise("198.51.100.5")) == ("198.51.100.5", 54321)
    assert asyncio.run(exercise("127.0.0.1"))[0] == "203.0.113.19"
