"""Unit tests for an isolated signed-admission prototype. No Docker/DB/network."""

import base64
import json
from uuid import uuid4

import pytest

from app.workers.job_admission import (
    AdmissionRejected,
    AdmissionResult,
    AdmissionService,
    MemoryAdmissionStore,
)

SERVICE_KEY = b"A" * 32
OTHER_KEY = b"B" * 32
NOW = 1_800_000_000


def envelope(
    *,
    operation: str = "submit",
    user_id: str | None = None,
    tenant_id: str = "tenant1",
    job_id: str | None = None,
    idem: str = "key_123",
    content: bytes = b"synthetic test only",
) -> bytes:
    subject = {"user_id": user_id or str(uuid4()), "tenant_id": tenant_id}
    data: dict[str, object] = {
        "version": 1,
        "operation": operation,
        "request_id": str(uuid4()),
        "subject": subject,
    }
    if operation == "submit":
        data["idempotency_key"] = idem
        data["payload"] = {
            "filename": "synthetic.txt",
            "content_b64": base64.b64encode(content).decode(),
        }
    else:
        data["job_id"] = job_id
    return json.dumps(data).encode()


def build(
    *, global_limit: int = 2, user_limit: int = 1
) -> tuple[AdmissionService, MemoryAdmissionStore]:
    store = MemoryAdmissionStore(global_limit=global_limit, user_limit=user_limit)
    return AdmissionService({"api": SERVICE_KEY}, store, clock=lambda: NOW), store


def send(
    service: AdmissionService,
    raw: bytes,
    *,
    nonce: str | None = None,
    timestamp: int = NOW,
    key: bytes = SERVICE_KEY,
    service_id: str = "api",
) -> AdmissionResult:
    nonce = nonce or uuid4().hex
    return service.admit(
        raw,
        service_id=service_id,
        timestamp=timestamp,
        nonce=nonce,
        signature=AdmissionService.signature(key, raw, timestamp, nonce),
    )


def test_valid_signed_submit_creates_queued_job() -> None:
    service, _ = build()
    result = send(service, envelope())
    assert result.status == "queued"
    assert result.reused is False


@pytest.mark.parametrize(
    "change",
    ["invalid_key", "unknown_service", "old_timestamp", "future_timestamp"],
)
def test_invalid_identity_rejected(change: str) -> None:
    service, _ = build()
    raw = envelope()
    with pytest.raises(AdmissionRejected, match="ADMISSION_UNAUTHORIZED"):
        if change == "invalid_key":
            send(service, raw, key=OTHER_KEY)
        elif change == "unknown_service":
            send(service, raw, service_id="unknown")
        elif change == "old_timestamp":
            send(service, raw, timestamp=NOW - 61)
        else:
            send(service, raw, timestamp=NOW + 61)


def test_unsigned_payload_tampering_rejected() -> None:
    service, _ = build()
    raw = envelope()
    nonce = uuid4().hex
    signed = AdmissionService.signature(SERVICE_KEY, raw, NOW, nonce)
    with pytest.raises(AdmissionRejected, match="ADMISSION_UNAUTHORIZED"):
        service.admit(raw + b" ", service_id="api", timestamp=NOW, nonce=nonce, signature=signed)


def test_nonce_replay_rejected() -> None:
    service, _ = build()
    raw = envelope()
    nonce = uuid4().hex
    send(service, raw, nonce=nonce)
    with pytest.raises(AdmissionRejected, match="ADMISSION_REPLAY"):
        send(service, raw, nonce=nonce)


def test_invalid_body_does_not_consume_nonce() -> None:
    service, _ = build()
    nonce = uuid4().hex
    with pytest.raises(AdmissionRejected, match="ADMISSION_INVALID"):
        send(service, b"not-json", nonce=nonce)
    result = send(service, envelope(), nonce=nonce)
    assert result.status == "queued"


def test_idempotency_reuses_job_for_same_owner_and_content() -> None:
    service, _ = build()
    user_id = str(uuid4())
    raw = envelope(user_id=user_id)
    first = send(service, raw)
    again = send(service, envelope(user_id=user_id))
    assert again.job_id == first.job_id
    assert again.reused is True


def test_idempotency_conflict_rejected() -> None:
    service, _ = build()
    user_id = str(uuid4())
    send(service, envelope(user_id=user_id))
    with pytest.raises(AdmissionRejected, match="ADMISSION_CONFLICT"):
        send(service, envelope(user_id=user_id, content=b"other synthetic contents"))


def test_global_capacity_is_bounded() -> None:
    service, _ = build(global_limit=1)
    send(service, envelope())
    with pytest.raises(AdmissionRejected, match="ADMISSION_BUSY"):
        send(service, envelope())


def test_per_user_capacity_is_bounded() -> None:
    service, _ = build(global_limit=3, user_limit=1)
    user_id = str(uuid4())
    send(service, envelope(user_id=user_id, idem="one"))
    with pytest.raises(AdmissionRejected, match="ADMISSION_BUSY"):
        send(service, envelope(user_id=user_id, idem="two"))


def test_owner_can_status_and_cancel() -> None:
    service, _ = build()
    user_id = str(uuid4())
    first = send(service, envelope(user_id=user_id))
    status = send(
        service,
        envelope(operation="status", user_id=user_id, job_id=str(first.job_id)),
    )
    assert status.status == "queued"
    cancelled = send(
        service,
        envelope(operation="cancel", user_id=user_id, job_id=str(first.job_id)),
    )
    assert cancelled.status == "cancelled"
    assert (
        send(
            service, envelope(operation="cancel", user_id=user_id, job_id=str(first.job_id))
        ).status
        == "cancelled"
    )


@pytest.mark.parametrize("operation", ["status", "cancel"])
def test_cross_user_and_cross_tenant_denied(operation: str) -> None:
    service, _ = build()
    user_id = str(uuid4())
    first = send(service, envelope(user_id=user_id))
    for wrong_user, wrong_tenant in (
        (str(uuid4()), "tenant1"),
        (user_id, "tenant2"),
    ):
        with pytest.raises(AdmissionRejected, match="ADMISSION_NOT_FOUND"):
            send(
                service,
                envelope(
                    operation=operation,
                    user_id=wrong_user,
                    tenant_id=wrong_tenant,
                    job_id=str(first.job_id),
                ),
            )


def test_no_runtime_or_parser_is_called(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import resume_worker

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("the parser must not be started")

    monkeypatch.setattr(resume_worker, "parse_in_worker", forbidden)
    service, _ = build()
    send(service, envelope())
