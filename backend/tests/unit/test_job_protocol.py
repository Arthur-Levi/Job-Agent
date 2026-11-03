"""Synthetic-only tests for the pure worker job protocol validator."""

import base64
import json
from collections.abc import Callable
from copy import deepcopy
from uuid import uuid4

import pytest

from app.workers.job_protocol import (
    MAX_DOCUMENT_BYTES,
    MAX_ENVELOPE_BYTES,
    ProtocolValidationError,
    validate_job_envelope,
)


def valid_submit() -> dict[str, object]:
    return {
        "version": 1,
        "operation": "submit",
        "request_id": str(uuid4()),
        "idempotency_key": "synthetic-123",
        "subject": {"user_id": str(uuid4()), "tenant_id": "synthetic_tenant"},
        "payload": {
            "filename": "synthetic.txt",
            "content_b64": base64.b64encode(b"synthetic test resume").decode(),
        },
    }


def encode(value: dict[str, object]) -> bytes:
    return json.dumps(value).encode()


def test_valid_submit_decodes_document() -> None:
    parsed = validate_job_envelope(encode(valid_submit()))
    assert parsed.operation == "submit"
    assert parsed.document == b"synthetic test resume"
    assert parsed.filename == "synthetic.txt"
    assert parsed.job_id is None


@pytest.mark.parametrize("operation", ["status", "cancel"])
def test_valid_status_and_cancel(operation: str) -> None:
    data = valid_submit()
    data["operation"] = operation
    data["job_id"] = str(uuid4())
    data.pop("idempotency_key")
    data.pop("payload")
    parsed = validate_job_envelope(encode(data))
    assert parsed.operation == operation
    assert parsed.document is None
    assert parsed.job_id is not None


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d.update(version=True),
        lambda d: d.update(version=2),
        lambda d: d.update(operation="docker"),
        lambda d: d.update(command="rm"),
        lambda d: d.update(image="python"),
        lambda d: d.update(request_id="not-uuid"),
        lambda d: d.update(idempotency_key="contains spaces"),
        lambda d: d.update(subject={"user_id": "fake", "tenant_id": "tenant"}),
        lambda d: d.update(subject={"user_id": str(uuid4()), "tenant_id": "../../x"}),
        lambda d: d.update(payload={"filename": "../evil.txt", "content_b64": "eA=="}),
        lambda d: d.update(payload={"filename": "synthetic.exe", "content_b64": "eA=="}),
        lambda d: d.update(payload={"filename": "synthetic.txt", "content_b64": "***"}),
        lambda d: d.update(payload={"filename": "synthetic.txt", "content_b64": ""}),
    ],
)
def test_rejects_invalid_submit(mutation: Callable[[dict[str, object]], None]) -> None:
    data = deepcopy(valid_submit())
    mutation(data)
    with pytest.raises(ProtocolValidationError, match="invalid envelope"):
        validate_job_envelope(encode(data))


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"not-json",
        b"[]",
        b"null",
        b"{\"version\":1,\"version\":1}",
        b"\xff",
        b"x" * (MAX_ENVELOPE_BYTES + 1),
    ],
)
def test_rejects_bad_serialization(raw: bytes) -> None:
    with pytest.raises(ProtocolValidationError):
        validate_job_envelope(raw)


def test_rejects_oversized_decoded_document() -> None:
    data = valid_submit()
    data["payload"] = {
        "filename": "synthetic.txt",
        "content_b64": base64.b64encode(b"x" * (MAX_DOCUMENT_BYTES + 1)).decode(),
    }
    with pytest.raises(ProtocolValidationError):
        validate_job_envelope(encode(data))


def test_status_rejects_submit_payload() -> None:
    data = valid_submit()
    data["operation"] = "status"
    data["job_id"] = str(uuid4())
    with pytest.raises(ProtocolValidationError):
        validate_job_envelope(encode(data))


def test_validator_is_pure_and_does_not_start_parser(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import resume_worker

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("parser should not run")

    monkeypatch.setattr(resume_worker, "parse_in_worker", forbidden)
    validate_job_envelope(encode(valid_submit()))
