"""E2.2-F.1.2: synthetic gateway-to-broker authentication; NOT a live broker.

Only authenticates a bounded transport envelope from a registered gateway UID.
No parser, Docker, public listener, filesystem socket, DB or job execution.
ReplayStore must be durable/atomic before any real deployment.
"""

import hashlib
import hmac
import json
import re
import socket
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from app.workers.gateway_identity import GatewayIdentityGate
from app.workers.job_protocol import (
    MAX_ENVELOPE_BYTES,
    ProtocolValidationError,
    validate_job_envelope,
)

BROKER_HMAC_DOMAIN = b"jobagent-gateway-broker-v1\n"
MAX_SKEW_SECONDS = 60
MAX_NONCE_LENGTH = 96
_NONCE = re.compile(r"^[A-Za-z0-9]{16,96}$")


class BrokerTransportRejected(Exception):
    """Opaque authentication failure; never include caller-controlled bytes."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class ReplayStore(Protocol):
    def accept_nonce(self, service_id: str, nonce: str, now: int) -> bool: ...


@dataclass(frozen=True)
class GatewayWorkload:
    service_id: str
    uid: int
    gid: int
    key: bytes


@dataclass(frozen=True)
class AuthenticatedForward:
    operation: str
    tenant_id: str
    user_id: str
    digest: str


def sign_forward(key: bytes, payload: bytes, *, timestamp: int, nonce: str) -> str:
    """Domain-separated HMAC; no user data or secret enters returned metadata."""
    material = (
        BROKER_HMAC_DOMAIN
        + str(timestamp).encode("ascii")
        + b"\n"
        + nonce.encode("ascii")
        + b"\n"
        + hashlib.sha256(payload).digest()
    )
    return hmac.new(key, material, hashlib.sha256).hexdigest()


class BrokerTransportGate:
    """Receive only gateway-originated, signed, non-replayed synthetic jobs.

    The broker's private 0700/0600 socket is NOT opened here. A future
    independent broker-side acceptor must enforce access before calling admit.
    """

    def __init__(
        self,
        workload: GatewayWorkload,
        replay: ReplayStore,
        *,
        broker_uid: int,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if (
            not workload.service_id
            or workload.uid <= 0
            or workload.gid <= 0
            or broker_uid <= 0
            or workload.uid == broker_uid
            or len(workload.key) < 32
        ):
            raise ValueError("invalid or unseparated broker transport identities")
        self._workload = workload
        self._replay = replay
        self._clock = clock

    def admit(
        self,
        connection: socket.socket,
        payload: bytes,
        *,
        service_id: str,
        timestamp: int,
        nonce: str,
        signature: str,
    ) -> AuthenticatedForward:
        if (
            service_id != self._workload.service_id
            or GatewayIdentityGate.peer_identity(connection)
            != (self._workload.uid, self._workload.gid)
            or type(timestamp) is not int
            or abs(self._clock() - timestamp) > MAX_SKEW_SECONDS
            or not isinstance(nonce, str)
            or not _NONCE.fullmatch(nonce)
            or not isinstance(signature, str)
            or not re.fullmatch(r"[0-9a-f]{64}", signature)
            or not isinstance(payload, bytes)
            or not 0 < len(payload) <= MAX_ENVELOPE_BYTES
        ):
            raise BrokerTransportRejected("BROKER_UNAUTHORIZED")

        expected = sign_forward(self._workload.key, payload, timestamp=timestamp, nonce=nonce)
        if not hmac.compare_digest(expected, signature):
            raise BrokerTransportRejected("BROKER_UNAUTHORIZED")

        # Never accept arbitrary JSON: only the strict existing job envelope.
        try:
            job = validate_job_envelope(payload)
        except (ProtocolValidationError, ValueError):
            raise BrokerTransportRejected("BROKER_INVALID") from None
        # Replay state must be atomically shared across receiver processes in production.
        if not self._replay.accept_nonce(
            "broker:" + self._workload.service_id, nonce, int(self._clock())
        ):
            raise BrokerTransportRejected("BROKER_REPLAY")
        return AuthenticatedForward(
            operation=job.operation,
            tenant_id=job.tenant_id,
            user_id=str(job.user_id),
            digest=hashlib.sha256(payload).hexdigest(),
        )


def encode_signed_transport(
    payload: bytes,
    *,
    service_id: str,
    timestamp: int,
    nonce: str,
    key: bytes,
) -> bytes:
    """Encode a test-only signed envelope, never pass it to real resume_broker."""
    if not 0 < len(payload) <= MAX_ENVELOPE_BYTES:
        raise ValueError("invalid payload length")
    return json.dumps(
        {
            "version": 1,
            "service_id": service_id,
            "timestamp": timestamp,
            "nonce": nonce,
            "signature": sign_forward(key, payload, timestamp=timestamp, nonce=nonce),
            "payload_hex": payload.hex(),
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
