"""Two-hop signed staging relay contract; never launches a real parser or Docker."""

import base64
import hashlib
import json
import os
import secrets
import socket
import sys
import threading
import time
from uuid import uuid4

import pytest

from app.workers.broker_transport_auth import (
    BrokerTransportGate,
    BrokerTransportRejected,
    GatewayWorkload,
)
from app.workers.broker_transport_wire import receive_authenticated, send_frame
from app.workers.gateway_identity import AuthorizedWorkload, GatewayIdentityGate
from app.workers.job_admission import AdmissionService, MemoryAdmissionStore
from app.workers.secops_authenticated_chain import (
    ChainRejected,
    encode_api_message,
    relay_one,
)

API_KEY = b"synthetic-api-gateway-key-" + b"a" * 32
BROKER_KEY = b"synthetic-gateway-broker-key-" + b"b" * 32


def _payload() -> bytes:
    return json.dumps(
        {
            "version": 1,
            "operation": "submit",
            "request_id": str(uuid4()),
            "idempotency_key": secrets.token_hex(16),
            "subject": {"user_id": str(uuid4()), "tenant_id": "lab"},
            "payload": {
                "filename": "synthetic.txt",
                "content_b64": base64.b64encode(b"synthetic resume only").decode(),
            },
        },
        separators=(",", ":"),
    ).encode()


def _gates() -> tuple[GatewayIdentityGate, BrokerTransportGate]:
    uid, gid = os.getuid(), os.getgid()
    api = GatewayIdentityGate(
        (AuthorizedWorkload("api", uid, gid),),
        AdmissionService({"api": API_KEY}, MemoryAdmissionStore()),
        broker_uid=uid + 1,
    )
    broker = BrokerTransportGate(
        GatewayWorkload("gateway", uid, gid, BROKER_KEY),
        MemoryAdmissionStore(),
        broker_uid=uid + 1,
    )
    return api, broker


@pytest.fixture(autouse=True)
def _linux_unprivileged() -> None:
    if sys.platform != "linux" or os.geteuid() == 0:
        pytest.skip("Linux non-root SO_PEERCRED tests only")


def _run(
    raw: bytes,
    *,
    api_gate: GatewayIdentityGate | None = None,
    broker_gate: BrokerTransportGate | None = None,
    api_key: bytes = API_KEY,
    nonce: str | None = None,
    broker_reply: bytes | None = None,
) -> tuple[str, str]:
    gate_api, gate_broker = _gates()
    gate_api = api_gate or gate_api
    gate_broker = broker_gate or gate_broker
    client, gateway_in = socket.socketpair()
    gateway_out, broker_in = socket.socketpair()
    received: list[str] = []

    def broker() -> None:
        with broker_in:
            broker_in.settimeout(2)
            try:
                item = receive_authenticated(broker_in, gate_broker)
                received.append(item.digest)
                send_frame(
                    broker_in,
                    broker_reply
                    if broker_reply is not None
                    else ("ACCEPTED:" + item.digest).encode("ascii"),
                )
            except (OSError, BrokerTransportRejected):
                return

    worker = threading.Thread(target=broker, daemon=True)
    worker.start()
    result = "REJECTED"
    try:
        with client, gateway_in, gateway_out:
            client.settimeout(2)
            gateway_in.settimeout(2)
            gateway_out.settimeout(2)
            msg = encode_api_message(
                raw,
                api_service_id="api",
                api_secret=api_key,
                timestamp=int(time.time()),
                nonce=nonce or secrets.token_hex(16),
            )
            send_frame(client, msg)
            try:
                accepted = relay_one(
                    gateway_in,
                    broker_connect=lambda: gateway_out,
                    api_gate=gate_api,
                    gateway_service_id="gateway",
                    broker_secret=BROKER_KEY,
                )
                assert accepted.broker_acknowledged
                result = accepted.request_digest
            except ChainRejected:
                pass
    finally:
        worker.join(timeout=3)
    assert not worker.is_alive()
    return result, received[0] if received else ""


def test_authenticated_chain_reaches_correct_broker() -> None:
    raw = _payload()
    digest, broker_digest = _run(raw)
    assert digest == hashlib.sha256(raw).hexdigest()
    assert broker_digest == digest


def test_invalid_api_workload_signature_never_reaches_broker() -> None:
    assert _run(_payload(), api_key=b"c" * 48) == ("REJECTED", "")


def test_wrong_api_peer_identity_never_reaches_broker() -> None:
    _, broker = _gates()
    wrong = GatewayIdentityGate(
        (AuthorizedWorkload("api", os.getuid() + 100, os.getgid()),),
        AdmissionService({"api": API_KEY}, MemoryAdmissionStore()),
        broker_uid=os.getuid() + 1,
    )
    assert _run(_payload(), api_gate=wrong, broker_gate=broker) == ("REJECTED", "")


def test_forged_broker_ack_does_not_pass_gateway() -> None:
    digest, reached = _run(_payload(), broker_reply=b"ACCEPTED:wrong-digest")
    assert digest == "REJECTED"
    assert len(reached) == 64


def test_broker_rejection_never_acknowledged_by_gateway() -> None:
    digest, reached = _run(_payload(), broker_reply=b"REJECTED:BROKER_REPLAY")
    assert digest == "REJECTED"
    assert len(reached) == 64


def test_replayed_api_nonce_never_reaches_broker() -> None:
    api, broker = _gates()
    raw = _payload()
    nonce = secrets.token_hex(16)
    first, first_delivery = _run(raw, api_gate=api, broker_gate=broker, nonce=nonce)
    second, second_delivery = _run(raw, api_gate=api, broker_gate=broker, nonce=nonce)
    assert first == hashlib.sha256(raw).hexdigest()
    assert first_delivery == first
    assert second == "REJECTED"
    assert second_delivery == ""
