"""D2-E1.5 trusted proxy scope contract — no database or external network."""

import asyncio
from typing import Any, cast

from starlette.types import Message, Receive, Scope, Send
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware


def test_proxy_headers_only_from_trusted_peer() -> None:
    async def exercise(peer: str) -> tuple[str, int]:
        seen: list[tuple[str, int]] = []

        async def inner(scope: Scope, receive: Receive, send: Send) -> None:
            seen.append(scope["client"])

        app = ProxyHeadersMiddleware(cast(Any, inner), trusted_hosts=["127.0.0.1"])
        scope: Scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "scheme": "http",
            "headers": [(b"x-forwarded-for", b"203.0.113.19")],
            "client": (peer, 54321),
            "server": ("127.0.0.1", 18081),
        }

        async def receive() -> Message:
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: Message) -> None:
            return None

        await app(cast(Any, scope), cast(Any, receive), cast(Any, send))
        assert len(seen) == 1
        return seen[0]

    assert asyncio.run(exercise("198.51.100.5")) == ("198.51.100.5", 54321)
    assert asyncio.run(exercise("127.0.0.1"))[0] == "203.0.113.19"
