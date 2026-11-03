"""Pure, fail-closed validation of proposed worker job envelopes.

This module is NOT wired into the API or broker and provides NO authentication.
The transport must authenticate workload identity and bind subject to an
authorized session before calling this validator. Never log input envelopes.
"""

import base64
import binascii
import json
import re
from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID

MAX_ENVELOPE_BYTES = 3_000_000
MAX_DOCUMENT_BYTES = 2_000_000
MAX_FILENAME_CHARS = 180
MAX_IDEMPOTENCY_CHARS = 128
TENANT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


class ProtocolValidationError(ValueError):
    """Non-sensitive rejection; do not attach source payload to this error."""


@dataclass(frozen=True)
class ValidatedJob:
    version: Literal[1]
    operation: Literal["submit", "status", "cancel"]
    request_id: UUID
    user_id: UUID
    tenant_id: str
    idempotency_key: str | None
    job_id: UUID | None
    filename: str | None
    document: bytes | None


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProtocolValidationError("invalid envelope")
        result[key] = value
    return result


def _keys(value: Any, expected: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ProtocolValidationError("invalid envelope")
    return value


def _uuid(value: Any) -> UUID:
    if not isinstance(value, str):
        raise ProtocolValidationError("invalid envelope")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError) as exc:
        raise ProtocolValidationError("invalid envelope") from exc
    if str(parsed) != value or parsed.int == 0:
        raise ProtocolValidationError("invalid envelope")
    return parsed


def validate_job_envelope(raw: bytes) -> ValidatedJob:
    """Validate shape and size only. Does not authenticate or authorize.

    Bytes are bounded before JSON decoding. Duplicate keys and extra fields
    are rejected; operation-specific schemas have no command/image fields.
    """
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_ENVELOPE_BYTES:
        raise ProtocolValidationError("invalid envelope")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicate_keys)
    except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ProtocolValidationError("invalid envelope") from exc

    if not isinstance(value, dict):
        raise ProtocolValidationError("invalid envelope")
    operation = value.get("operation")
    if operation == "submit":
        fields = {"version", "operation", "request_id", "idempotency_key", "subject", "payload"}
    elif operation in {"status", "cancel"}:
        fields = {"version", "operation", "request_id", "subject", "job_id"}
    else:
        raise ProtocolValidationError("invalid envelope")
    envelope = _keys(value, fields)
    if type(envelope["version"]) is not int or envelope["version"] != 1:
        raise ProtocolValidationError("invalid envelope")

    request_id = _uuid(envelope["request_id"])
    subject = _keys(envelope["subject"], {"user_id", "tenant_id"})
    user_id = _uuid(subject["user_id"])
    tenant_id = subject["tenant_id"]
    if not isinstance(tenant_id, str) or not TENANT_PATTERN.fullmatch(tenant_id):
        raise ProtocolValidationError("invalid envelope")

    if operation == "submit":
        key = envelope["idempotency_key"]
        if (
            not isinstance(key, str)
            or len(key) > MAX_IDEMPOTENCY_CHARS
            or not IDEMPOTENCY_PATTERN.fullmatch(key)
        ):
            raise ProtocolValidationError("invalid envelope")
        payload = _keys(envelope["payload"], {"filename", "content_b64"})
        filename = payload["filename"]
        if (
            not isinstance(filename, str)
            or not 0 < len(filename) <= MAX_FILENAME_CHARS
            or any(ord(char) < 32 or char in "/\\\x7f" for char in filename)
            or filename in {".", ".."}
            or not filename.lower().endswith((".pdf", ".docx", ".txt"))
        ):
            raise ProtocolValidationError("invalid envelope")
        encoded = payload["content_b64"]
        if (
            not isinstance(encoded, str)
            or not encoded
            or len(encoded) > 4 * ((MAX_DOCUMENT_BYTES + 2) // 3)
            or not encoded.isascii()
        ):
            raise ProtocolValidationError("invalid envelope")
        try:
            document = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ProtocolValidationError("invalid envelope") from exc
        if not 0 < len(document) <= MAX_DOCUMENT_BYTES:
            raise ProtocolValidationError("invalid envelope")
        return ValidatedJob(1, "submit", request_id, user_id, tenant_id, key, None, filename, document)

    job_id = _uuid(envelope["job_id"])
    if operation == "status":
        return ValidatedJob(1, "status", request_id, user_id, tenant_id, None, job_id, None, None)
    return ValidatedJob(1, "cancel", request_id, user_id, tenant_id, None, job_id, None, None)
