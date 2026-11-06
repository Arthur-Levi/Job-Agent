"""F.1.2 synthetic Unix socket message delivery; no listener, Docker or parsing."""

import base64
import json
import os
import secrets
import socket
import struct
import sys
import threading
import time
from uuid import uuid4

import pytest

from app.workers.broker_transport_auth import (
    BrokerTransportGate,
    BrokerTransportRejected,
    GatewayWorkload,
    encode_signed_transport,
)
from app.workers.broker_transport_wire import read_frame, receive_authenticated, send_frame
from app.workers.job_admission import MemoryAdmissionStore

_KEY = b"f1-2-test-gateway-broker-key-only-0000000000000"


def payload() -> bytes:
    return json.dumps(
        {
            "version": 1,
            "operation": "submit",
            "request_id": str(uuid4()),
            "idempotency_key": uuid4().hex,
            "subject": {"user_id": str(uuid4()), "tenant_id": "synthetic"},
            "payload": {
                "filename": "synthetic.txt",
                "content_b64": base64.b64encode(b"not a real resume").decode(),
            },
        }
    ).encode()


def test_signed_message_reaches_synthetic_broker_and_replay_is_denied() -> None:
    if sys.platform != "linux" or os.getuid() == 0:
        pytest.skip("non-root Linux SO_PEERCRED only")
    gate = BrokerTransportGate(
        GatewayWorkload("synthetic-gateway", os.getuid(), os.getgid(), _KEY),
        MemoryAdmissionStore(),
        broker_uid=os.getuid() + 1,
    )
    raw = payload()
    timestamp = int(time.time())
    nonce = secrets.token_hex(16)
    frame = encode_signed_transport(
        raw, service_id="synthetic-gateway", timestamp=timestamp, nonce=nonce, key=_KEY
    )
    gateway_sock, broker_sock = socket.socketpair()
    replies: list[str] = []

    def serve() -> None:
        with broker_sock:
            broker_sock.settimeout(2)
            accepted = receive_authenticated(broker_sock, gate)
            assert accepted.tenant_id == "synthetic"
            send_frame(broker_sock, b"ACCEPTED:" + accepted.digest.encode())
            try:
                receive_authenticated(broker_sock, gate)
            except BrokerTransportRejected as exc:
                replies.append(exc.code)

    worker = threading.Thread(target=serve, daemon=True)
    worker.start()
    try:
        with gateway_sock:
            gateway_sock.settimeout(2)
            send_frame(gateway_sock, frame)
            answer = read_frame(gateway_sock, max_bytes=1024)
            assert answer.startswith(b"ACCEPTED:")
            send_frame(gateway_sock, frame)
    finally:
        worker.join(timeout=3)
    assert not worker.is_alive()
    assert replies == ["BROKER_REPLAY"]


def test_tampered_signed_wire_payload_is_rejected() -> None:
    if sys.platform != "linux" or os.getuid() == 0:
        pytest.skip("non-root Linux SO_PEERCRED only")
    gate = BrokerTransportGate(
        GatewayWorkload("synthetic-gateway", os.getuid(), os.getgid(), _KEY),
        MemoryAdmissionStore(),
        broker_uid=os.getuid() + 1,
    )
    frame = encode_signed_transport(
        payload(),
        service_id="synthetic-gateway",
        timestamp=int(time.time()),
        nonce=secrets.token_hex(16),
        key=_KEY,
    )
    tampered = json.loads(frame)
    tampered["payload_hex"] += "20"
    gateway_sock, broker_sock = socket.socketpair()
    with (
        gateway_sock,
        broker_sock,
        pytest.raises(BrokerTransportRejected, match="BROKER_UNAUTHORIZED"),
    ):
        send_frame(gateway_sock, json.dumps(tampered).encode())
        receive_authenticated(broker_sock, gate)


def test_oversized_wire_frame_is_rejected_before_body_read() -> None:
    receiver, sender = socket.socketpair()
    with receiver, sender, pytest.raises(BrokerTransportRejected, match="BROKER_FRAME_INVALID"):
        sender.sendall(struct.pack("!I", 0xFFFFFFFF))
        read_frame(receiver)
