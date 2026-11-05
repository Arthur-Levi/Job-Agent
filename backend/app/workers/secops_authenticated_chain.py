"""F.1.2.3: authenticated two-hop staging relay; no CV parser or live endpoint.

API workload -> gateway (SO_PEERCRED + API HMAC/nonce/admission) ->
broker (new HMAC domain + peer credentials + persistent nonce).

Wire helpers operate on *already accepted Unix sockets*. Production adapters must
validate authenticated user/tenant and consent before preparing the first hop.
No Docker access, parser invocation, or public route is introduced here.
"""

import json
import secrets
import socket
import time
from dataclasses import dataclass
from typing import Any

from app.workers.broker_transport_auth import (
    BrokerTransportRejected,
    encode_signed_transport,
)
from app.workers.broker_transport_wire import read_frame, send_frame
from app.workers.gateway_identity import GatewayIdentityGate
from app.workers.job_admission import AdmissionRejected, AdmissionService
from app.workers.job_protocol import MAX_ENVELOPE_BYTES, validate_job_envelope

_MAX_TRANSPORT_BYTES = 2 * MAX_ENVELOPE_BYTES + 4096
_FIELDS = {"version", "service_id", "timestamp", "nonce", "signature", "payload_hex"}


class ChainRejected(Exception):
    def __init__(self, code: str = "CHAIN_DENIED") -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ChainAcknowledgement:
    broker_acknowledged: bool
    request_digest: str


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate")
        result[key] = value
    return result


def _decode_frame(frame: bytes) -> tuple[bytes, str, int, str, str]:
    if len(frame) > _MAX_TRANSPORT_BYTES:
        raise ChainRejected()
    try:
        data = json.loads(frame, object_pairs_hook=_no_duplicate_keys)
        if (
            not isinstance(data, dict)
            or set(data) != _FIELDS
            or type(data["version"]) is not int
            or data["version"] != 1
            or not isinstance(data["service_id"], str)
            or type(data["timestamp"]) is not int
            or not isinstance(data["nonce"], str)
            or not isinstance(data["signature"], str)
            or not isinstance(data["payload_hex"], str)
            or len(data["payload_hex"]) > MAX_ENVELOPE_BYTES * 2
        ):
            raise ValueError("invalid metadata")
        payload = bytes.fromhex(data["payload_hex"])
    except (ValueError, TypeError, KeyError, UnicodeError):
        raise ChainRejected() from None
    return (
        payload,
        data["service_id"],
        data["timestamp"],
        data["nonce"],
        data["signature"],
    )


def encode_api_message(
    raw: bytes, *, api_service_id: str, api_secret: bytes, timestamp: int, nonce: str
) -> bytes:
    """Only a trusted API adapter may call this after independent user authorization."""
    validate_job_envelope(raw)
    if len(api_secret) < 32:
        raise ValueError("API credential is too short")
    return json.dumps(
        {
            "version": 1,
            "service_id": api_service_id,
            "timestamp": timestamp,
            "nonce": nonce,
            "signature": AdmissionService.signature(api_secret, raw, timestamp, nonce),
            "payload_hex": raw.hex(),
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def relay_one(
    api_connection: socket.socket,
    broker_connection: socket.socket,
    *,
    api_gate: GatewayIdentityGate,
    gateway_service_id: str,
    broker_secret: bytes,
) -> ChainAcknowledgement:
    """Fail closed unless both peer and both HMAC admissions succeed.

    Broker socket must be opened by gateway UID with an explicit scoped group.
    Nothing here opens the broker's separate 0700/0600 parser socket.
    """
    if len(broker_secret) < 32:
        raise ValueError("broker credential is too short")
    frame = read_frame(api_connection, max_bytes=_MAX_TRANSPORT_BYTES)
    raw, service, timestamp, nonce, signature = _decode_frame(frame)
    try:
        api_gate.admit(
            api_connection,
            raw,
            service_id=service,
            timestamp=timestamp,
            nonce=nonce,
            signature=signature,
        )
    except AdmissionRejected:
        raise ChainRejected() from None

    broker_frame = encode_signed_transport(
        raw,
        service_id=gateway_service_id,
        timestamp=int(time.time()),
        nonce=secrets.token_hex(16),
        key=broker_secret,
    )
    send_frame(broker_connection, broker_frame)
    try:
        response = read_frame(broker_connection, max_bytes=1024)
    except (OSError, BrokerTransportRejected):
        raise ChainRejected() from None
    # Broker acknowledgement may only name the digest of exactly this request.
    import hashlib

    digest = hashlib.sha256(raw).hexdigest()
    if response != ("ACCEPTED:" + digest).encode("ascii"):
        raise ChainRejected()
    return ChainAcknowledgement(True, digest)
