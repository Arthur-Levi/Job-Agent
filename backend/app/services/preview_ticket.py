"""User-bound short-lived preview tickets; no server-side draft storage.

Signed payload contains ORIGINAL parser fields. The client may edit only
editable fields, never origin/category. Tokens are integrity protected, NOT
encrypted: do not log, place in URLs, or expose to third parties.
"""
import base64
import hashlib
import hmac
import json
import time
from typing import Any

from app.core.errors import UnprocessableError

TOKEN_TTL_SECONDS = 900
MAX_TOKEN_LENGTH = 125_000


def _encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def sign_preview(
    preview: dict[str, Any], *, user_id: str, key: bytes, now: int | None = None
) -> str:
    original_items = [
        {
            "draft_id": item["draft_id"],
            "category": item["category"],
            "source_excerpt": item["source_excerpt"],
        }
        for item in preview["items"]
    ]
    payload = {
        "v": 1,
        "sub": user_id,
        "preview_id": preview["preview_id"],
        "format": preview["format"],
        "exp": (int(time.time()) if now is None else now) + TOKEN_TTL_SECONDS,
        "items": original_items,
    }
    body = _encode(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
    digest = _encode(hmac.new(key, b"job-agent-preview-v1." + body.encode(), hashlib.sha256).digest())
    token = body + "." + digest
    if len(token) > MAX_TOKEN_LENGTH:
        raise UnprocessableError("Prévia excede limite seguro", code="CV_PREVIEW_LIMIT")
    return token


def verify_preview(
    token: str, *, user_id: str, key: bytes, now: int | None = None
) -> dict[str, Any]:
    if not token or len(token) > MAX_TOKEN_LENGTH or token.count(".") != 1:
        raise UnprocessableError("Prévia inválida; envie o currículo novamente", code="CV_PREVIEW")
    encoded, signature = token.split(".", 1)
    expected = _encode(
        hmac.new(key, b"job-agent-preview-v1." + encoded.encode(), hashlib.sha256).digest()
    )
    if not hmac.compare_digest(expected, signature):
        raise UnprocessableError("Assinatura da prévia inválida", code="CV_PREVIEW")
    try:
        payload: dict[str, Any] = json.loads(_decode(encoded))
    except (ValueError, UnicodeDecodeError, TypeError):
        raise UnprocessableError("Prévia malformada", code="CV_PREVIEW") from None
    timestamp = int(time.time()) if now is None else now
    if (
        payload.get("v") != 1
        or payload.get("sub") != user_id
        or not isinstance(payload.get("exp"), int)
        or not timestamp < payload["exp"] <= timestamp + TOKEN_TTL_SECONDS
        or payload.get("format") not in ("txt", "pdf", "docx")
        or not isinstance(payload.get("items"), list)
        or len(payload["items"]) > 40
    ):
        raise UnprocessableError("Prévia expirada ou não autorizada", code="CV_PREVIEW")
    return payload
