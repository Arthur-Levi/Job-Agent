"""E2.2-F.1.2 synthetic signed transport rejection matrix; no real broker."""

import base64
import json
import os
import secrets
import socket
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from uuid import uuid4

import pytest

from app.workers.broker_transport_auth import (
    BrokerTransportGate,
    BrokerTransportRejected,
    GatewayWorkload,
    sign_forward,
)
from app.workers.job_admission import AdmissionService, MemoryAdmissionStore

KEY = b"synthetic-gateway-secret-not-for-deployment-" + b"x" * 16


@contextmanager
def sockets() -> Iterator[socket.socket]:
    first, second = socket.socketpair()
    with first, second:
        yield first


def job_payload() -> bytes:
    return json.dumps(
        {
            "version": 1,
            "operation": "submit",
            "request_id": str(uuid4()),
            "idempotency_key": uuid4().hex,
            "subject": {"tenant_id": "synthetic", "user_id": str(uuid4())},
            "payload": {
                "filename": "fake.txt",
                "content_b64": base64.b64encode(b"SYNTHETIC ONLY").decode("ascii"),
            },
        }
    ).encode()


@pytest.fixture
def gateway() -> BrokerTransportGate:
    if sys.platform != "linux" or os.geteuid() == 0:
        pytest.skip("Requires non-root Linux SO_PEERCRED for this unit test")
    return BrokerTransportGate(
        GatewayWorkload("gateway-synthetic", os.getuid(), os.getgid(), KEY),
        MemoryAdmissionStore(),
        broker_uid=os.getuid() + 1,
    )


def submit(
    gate: BrokerTransportGate,
    sock: socket.socket,
    raw: bytes,
    *,
    service_id: str = "gateway-synthetic",
    timestamp: int | None = None,
    nonce: str | None = None,
    signature: str | None = None,
) -> str:
    ts = int(time.time()) if timestamp is None else timestamp
    n = secrets.token_hex(16) if nonce is None else nonce
    sig = sign_forward(KEY, raw, timestamp=ts, nonce=n) if signature is None else signature
    result = gate.admit(
        sock,
        raw,
        service_id=service_id,
        timestamp=ts,
        nonce=n,
        signature=sig,
    )
    return result.digest


def test_valid_gateway_message_is_accepted(gateway: BrokerTransportGate) -> None:
    raw = job_payload()
    with sockets() as peer:
        assert submit(gateway, peer, raw)


def test_mutated_payload_is_denied(gateway: BrokerTransportGate) -> None:
    raw = job_payload()
    now = int(time.time())
    nonce = secrets.token_hex(16)
    sig = sign_forward(KEY, raw, timestamp=now, nonce=nonce)
    mutated = raw.replace(b"SYNTHETIC ONLY", b"ALTERED DATA") if b"SYNTHETIC ONLY" in raw else raw + b" "
    with (
        sockets() as peer,
        pytest.raises(BrokerTransportRejected, match="BROKER_UNAUTHORIZED"),
    ):
        submit(gateway, peer, mutated, timestamp=now, nonce=nonce, signature=sig)


def test_replayed_nonce_is_denied(gateway: BrokerTransportGate) -> None:
    raw = job_payload()
    now = int(time.time())
    nonce = secrets.token_hex(16)
    with sockets() as peer:
        submit(gateway, peer, raw, timestamp=now, nonce=nonce)
        with pytest.raises(BrokerTransportRejected, match="BROKER_REPLAY"):
            submit(gateway, peer, raw, timestamp=now, nonce=nonce)


@pytest.mark.parametrize(
    "condition",
    ["unknown_service", "wrong_uid", "expired", "future", "malformed_sig", "bad_body"],
)
def test_denied_gateway_or_signature(
    gateway: BrokerTransportGate, condition: str
) -> None:
    raw = job_payload()
    with sockets() as peer:
        if condition == "wrong_uid":
            class RejectPeer(BrokerTransportGate):
                def admit(  # type: ignore[override]
                    self, connection: socket.socket, payload: bytes, **kwargs: object
                ) -> object:
                    return super().admit(connection, payload, **kwargs)  # type: ignore[arg-type]

            # Distinct fake service registry UID; kernel socket identity remains unchanged.
            gate = BrokerTransportGate(
                GatewayWorkload("gateway-synthetic", os.getuid() + 99, os.getgid(), KEY),
                MemoryAdmissionStore(),
                broker_uid=os.getuid() + 1,
            )
        else:
            gate = gateway
        with pytest.raises(BrokerTransportRejected):
            if condition == "unknown_service":
                submit(gate, peer, raw, service_id="attacker")
            elif condition == "expired":
                submit(gate, peer, raw, timestamp=int(time.time()) - 120)
            elif condition == "future":
                submit(gate, peer, raw, timestamp=int(time.time()) + 120)
            elif condition == "malformed_sig":
                submit(gate, peer, raw, signature="a" * 64)
            elif condition == "bad_body":
                submit(gate, peer, b"not-json")
            else:
                submit(gate, peer, raw)


def test_signature_not_reusable_across_admission_protocols() -> None:
    raw = job_payload()
    timestamp = int(time.time())
    nonce = secrets.token_hex(16)
    api_sig = AdmissionService.signature(KEY, raw, timestamp, nonce)
    broker_sig = sign_forward(KEY, raw, timestamp=timestamp, nonce=nonce)
    assert api_sig != broker_sig


def test_broker_and_gateway_cannot_share_uid() -> None:
    if os.geteuid() == 0:
        pytest.skip("nonroot identity required")
    with pytest.raises(ValueError, match="unseparated"):
        BrokerTransportGate(
            GatewayWorkload("gateway-synthetic", os.getuid(), os.getgid(), KEY),
            MemoryAdmissionStore(),
            broker_uid=os.getuid(),
        )
