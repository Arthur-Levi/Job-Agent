"""F.1.2.4-B authenticated synthetic broker/parser contract; no Docker or CVs."""

import base64
import hashlib
import json
import os
import socket
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.services.resume_preview import build_preview
from app.workers.broker_transport_auth import (
    BrokerTransportGate,
    GatewayWorkload,
    encode_signed_transport,
)
from app.workers.broker_transport_wire import send_frame
from app.workers.secops_f124b_broker_parser import (
    SYNTHETIC_TENANT,
    SYNTHETIC_USER,
    SyntheticDispatchRejected,
    dispatch_synthetic_authenticated,
)
from app.workers.secops_synthetic_parser_lab import synthetic_cases


class MemoryReplay:
    def __init__(self) -> None:
        self.seen: set[tuple[str, str]] = set()

    def accept_nonce(self, service_id: str, nonce: str, now: int) -> bool:
        marker = (service_id, nonce)
        if marker in self.seen:
            return False
        self.seen.add(marker)
        return True


@pytest.fixture
def identity() -> tuple[BrokerTransportGate, bytes]:
    key = b"only-for-synthetic-broker-lab-32-bytes!!!"
    gate = BrokerTransportGate(
        GatewayWorkload(
            service_id="synthetic-gateway",
            uid=os.getuid(),
            gid=os.getgid(),
            key=key,
        ),
        MemoryReplay(),
        broker_uid=os.getuid() + 1000,
    )
    return gate, key


def _envelope(
    *,
    filename: str = "fictional.txt",
    data: bytes | None = None,
    tenant: str = SYNTHETIC_TENANT,
    user: str = SYNTHETIC_USER,
    operation: str = "submit",
) -> bytes:
    fixture = synthetic_cases()[0][1]
    return json.dumps(
        {
            "version": 1,
            "operation": operation,
            "request_id": str(uuid4()),
            "idempotency_key": "synthetic-only",
            "subject": {"user_id": user, "tenant_id": tenant},
            "payload": {
                "filename": filename,
                "content_b64": base64.b64encode(fixture if data is None else data).decode(),
            },
        },
        separators=(",", ":"),
    ).encode()


def _frame(
    raw: bytes,
    key: bytes,
    *,
    nonce: str | None = None,
    signature_key: bytes | None = None,
) -> bytes:
    return encode_signed_transport(
        raw,
        service_id="synthetic-gateway",
        timestamp=int(time.time()),
        nonce=nonce or uuid4().hex,
        key=signature_key or key,
    )


@contextmanager
def _socket_pair() -> Iterator[tuple[socket.socket, socket.socket]]:
    sender, receiver = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        yield sender, receiver
    finally:
        sender.close()
        receiver.close()


def _synthetic_executor(job: Any) -> dict[str, Any]:
    return {"ok": True, "preview": build_preview(job.filename, job.document)}


def test_authenticated_synthetic_only_dispatch(identity: tuple[BrokerTransportGate, bytes]) -> None:
    gate, key = identity
    raw = _envelope()
    with _socket_pair() as (sender, receiver):
        send_frame(sender, _frame(raw, key))
        result = dispatch_synthetic_authenticated(
            receiver, gate=gate, attestation=lambda: True, executor=_synthetic_executor
        )
    assert result.request_digest == hashlib.sha256(raw).hexdigest()
    assert result.format == "txt"
    assert "experience" in result.sections_detected
    assert result.item_count > 0
    assert "Fictional Company" not in repr(result)


@pytest.mark.parametrize(
    "scenario",
    ["bad_signature", "real_document", "other_tenant", "other_user"],
)
def test_denied_before_attestation_or_executor(
    identity: tuple[BrokerTransportGate, bytes], scenario: str
) -> None:
    gate, key = identity
    raw = _envelope()
    wrong_key: bytes | None = None
    if scenario == "bad_signature":
        wrong_key = b"x" * 40
    if scenario == "real_document":
        raw = _envelope(data=b"Professional Experience\nReal human content not allowed")
    if scenario == "other_tenant":
        raw = _envelope(tenant="actual-tenant")
    if scenario == "other_user":
        raw = _envelope(user=str(uuid4()))
    proof = Mock(return_value=True)
    run = Mock(side_effect=_synthetic_executor)
    with _socket_pair() as (sender, receiver):
        send_frame(sender, _frame(raw, key, signature_key=wrong_key))
        with pytest.raises(SyntheticDispatchRejected, match="F124B_DENIED"):
            dispatch_synthetic_authenticated(
                receiver, gate=gate, attestation=proof, executor=run
            )
    proof.assert_not_called()
    run.assert_not_called()


def test_no_parser_without_isolation(
    identity: tuple[BrokerTransportGate, bytes],
) -> None:
    gate, key = identity
    proof = Mock(return_value=False)
    run = Mock()
    with _socket_pair() as (sender, receiver):
        send_frame(sender, _frame(_envelope(), key))
        with pytest.raises(SyntheticDispatchRejected, match="F124B_SANDBOX_REQUIRED"):
            dispatch_synthetic_authenticated(
                receiver, gate=gate, attestation=proof, executor=run
            )
    proof.assert_called_once()
    run.assert_not_called()


def test_replay_is_denied_before_executor(
    identity: tuple[BrokerTransportGate, bytes],
) -> None:
    gate, key = identity
    signed = _frame(_envelope(), key, nonce="a" * 32)
    for count in range(2):
        run = Mock(side_effect=_synthetic_executor)
        with _socket_pair() as (sender, receiver):
            send_frame(sender, signed)
            if count == 0:
                dispatch_synthetic_authenticated(
                    receiver, gate=gate, attestation=lambda: True, executor=run
                )
                run.assert_called_once()
            else:
                with pytest.raises(SyntheticDispatchRejected, match="F124B_DENIED"):
                    dispatch_synthetic_authenticated(
                        receiver, gate=gate, attestation=lambda: True, executor=run
                    )
                run.assert_not_called()


def test_bounded_concurrency_fail_closed(
    identity: tuple[BrokerTransportGate, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.workers.secops_f124b_broker_parser as module

    gate, key = identity
    semaphore = Mock()
    semaphore.acquire.return_value = False
    monkeypatch.setattr(module, "_PARSER_SLOTS", semaphore)
    run = Mock()
    with _socket_pair() as (sender, receiver):
        send_frame(sender, _frame(_envelope(), key))
        with pytest.raises(SyntheticDispatchRejected, match="F124B_BUSY"):
            dispatch_synthetic_authenticated(
                receiver, gate=gate, attestation=lambda: True, executor=run
            )
    run.assert_not_called()
    semaphore.release.assert_not_called()


def test_crash_does_not_leak_contents_or_semaphore(
    identity: tuple[BrokerTransportGate, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.workers.secops_f124b_broker_parser as module

    gate, key = identity
    semaphore = Mock()
    semaphore.acquire.return_value = True
    monkeypatch.setattr(module, "_PARSER_SLOTS", semaphore)
    with _socket_pair() as (sender, receiver):
        send_frame(sender, _frame(_envelope(), key))
        with pytest.raises(SyntheticDispatchRejected, match="F124B_EXECUTOR_UNAVAILABLE") as exc:
            dispatch_synthetic_authenticated(
                receiver,
                gate=gate,
                attestation=lambda: True,
                executor=lambda job: (_ for _ in ()).throw(RuntimeError("private data!")),
            )
    assert "private data" not in str(exc.value)
    semaphore.release.assert_called_once()


def test_default_isolation_gate_refuses_without_explicit_opt_in(
    identity: tuple[BrokerTransportGate, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SECOPS_F124_ACK", raising=False)
    gate, key = identity
    with _socket_pair() as (sender, receiver):
        send_frame(sender, _frame(_envelope(), key))
        with pytest.raises(SyntheticDispatchRejected, match="F124B_SANDBOX_REQUIRED"):
            dispatch_synthetic_authenticated(
                receiver, gate=gate, executor=Mock()
            )


def test_invalid_executor_output_is_rejected(
    identity: tuple[BrokerTransportGate, bytes]
) -> None:
    gate, key = identity
    with _socket_pair() as (sender, receiver):
        send_frame(sender, _frame(_envelope(), key))
        with pytest.raises(SyntheticDispatchRejected, match="F124B_EXECUTOR_UNAVAILABLE"):
            dispatch_synthetic_authenticated(
                receiver,
                gate=gate,
                attestation=lambda: True,
                executor=lambda job: {"ok": True, "preview": {"format": "pdf"}},
            )
