"""F.1 synthetic IPC gate tests; no network listener, Docker, CV or DB."""

import base64
import json
import os
import secrets
import socket
import sys
import time
from uuid import uuid4

import pytest

from app.workers.gateway_identity import AuthorizedWorkload, GatewayIdentityGate
from app.workers.job_admission import (
    AdmissionRejected,
    AdmissionService,
    MemoryAdmissionStore,
)


def envelope() -> bytes:
    return json.dumps(
        {
            "version": 1,
            "operation": "submit",
            "request_id": str(uuid4()),
            "idempotency_key": uuid4().hex,
            "subject": {"tenant_id": "synthetic", "user_id": str(uuid4())},
            "payload": {
                "filename": "synthetic.txt",
                "content_b64": base64.b64encode(b"fake data only").decode("ascii"),
            },
        }
    ).encode("utf-8")


@pytest.fixture()
def gate() -> tuple[GatewayIdentityGate, bytes]:
    if sys.platform != "linux" or os.getuid() == 0:
        pytest.skip("Linux non-root peer credentials required")
    key = secrets.token_bytes(32)
    service = AdmissionService({"test-api": key}, MemoryAdmissionStore())
    permitted = AuthorizedWorkload("test-api", os.getuid(), os.getgid())
    return GatewayIdentityGate((permitted,), service, broker_uid=os.getuid() + 1), key


def authenticate(
    gate: GatewayIdentityGate,
    key: bytes,
    client: socket.socket,
    *,
    service_id: str = "test-api",
    bad_signature: bool = False,
) -> None:
    payload = envelope()
    now = int(time.time())
    nonce = secrets.token_hex(16)
    signature = AdmissionService.signature(key, payload, now, nonce)
    if bad_signature:
        signature = "0" * 64 if signature != "0" * 64 else "1" * 64
    gate.admit(
        client,
        payload,
        service_id=service_id,
        timestamp=now,
        nonce=nonce,
        signature=signature,
    )


def test_linux_peer_credential_and_signed_envelope(
    gate: tuple[GatewayIdentityGate, bytes],
) -> None:
    checker, key = gate
    with socket.socketpair() as (client, _other):
        assert checker.peer_identity(client) == (os.getuid(), os.getgid())
        authenticate(checker, key, client)


def test_unknown_workload_identity_is_denied(gate: tuple[GatewayIdentityGate, bytes]) -> None:
    checker, key = gate
    with socket.socketpair() as (client, _other):
        with pytest.raises(AdmissionRejected, match="GATEWAY_UNAUTHORIZED"):
            authenticate(checker, key, client, service_id="fake-api")


def test_invalid_signature_is_denied(gate: tuple[GatewayIdentityGate, bytes]) -> None:
    checker, key = gate
    with socket.socketpair() as (client, _other):
        with pytest.raises(AdmissionRejected, match="ADMISSION_UNAUTHORIZED"):
            authenticate(checker, key, client, bad_signature=True)


def test_separate_registered_os_identity_is_required() -> None:
    if os.getuid() == 0:
        pytest.skip("non-root identity required")
    store = MemoryAdmissionStore()
    admission = AdmissionService({"test-api": secrets.token_bytes(32)}, store)
    registered = AuthorizedWorkload("test-api", os.getuid(), os.getgid())
    with pytest.raises(ValueError, match="unseparated"):
        GatewayIdentityGate((registered,), admission, broker_uid=os.getuid())


def test_peer_uid_mismatch_is_rejected(gate: tuple[GatewayIdentityGate, bytes]) -> None:
    checker, key = gate
    with socket.socketpair() as (client, _other):
        # Fake only the kernel credential response. No privilege or UID changes.
        class WrongPeer(GatewayIdentityGate):
            @staticmethod
            def peer_identity(sock: socket.socket) -> tuple[int, int]:
                return os.getuid() + 50, os.getgid()

        wrong = WrongPeer(
            (AuthorizedWorkload("test-api", os.getuid(), os.getgid()),),
            checker._admission,  # noqa: SLF001
            broker_uid=os.getuid() + 1,
        )
        with pytest.raises(AdmissionRejected, match="GATEWAY_UNAUTHORIZED"):
            authenticate(wrong, key, client)
