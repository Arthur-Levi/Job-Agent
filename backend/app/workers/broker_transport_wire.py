"""E2.2-F.1.2 synthetic bounded request/response over already accepted Unix sockets.

Not wired to the real resume broker or a network/filesystem listener.
"""

import json
import socket
import struct

from app.workers.broker_transport_auth import (
    AuthenticatedForward,
    BrokerTransportGate,
    BrokerTransportRejected,
)
from app.workers.job_protocol import MAX_ENVELOPE_BYTES

MAX_SIGNED_FRAME = 2 * MAX_ENVELOPE_BYTES + 4096
MAX_REPLY = 1024


def _exact(sock: socket.socket, size: int) -> bytes:
    buf = bytearray()
    while len(buf) < size:
        chunk = sock.recv(min(65536, size - len(buf)))
        if not chunk:
            raise BrokerTransportRejected("BROKER_TRANSPORT_CLOSED")
        buf.extend(chunk)
    return bytes(buf)


def send_frame(sock: socket.socket, payload: bytes) -> None:
    if not payload or len(payload) > MAX_SIGNED_FRAME:
        raise BrokerTransportRejected("BROKER_FRAME_INVALID")
    sock.sendall(struct.pack("!I", len(payload)) + payload)


def read_frame(sock: socket.socket, *, max_bytes: int = MAX_SIGNED_FRAME) -> bytes:
    length = struct.unpack("!I", _exact(sock, 4))[0]
    if length < 1 or length > max_bytes:
        raise BrokerTransportRejected("BROKER_FRAME_INVALID")
    return _exact(sock, length)


def _reject_duplicate_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate field")
        result[key] = value
    return result


def receive_authenticated(sock: socket.socket, gate: BrokerTransportGate) -> AuthenticatedForward:
    """Authenticate entire frame before returning metadata; never start a parser."""
    raw = read_frame(sock)
    try:
        data = json.loads(raw, object_pairs_hook=_reject_duplicate_fields)
        if (
            not isinstance(data, dict)
            or set(data)
            != {"version", "service_id", "timestamp", "nonce", "signature", "payload_hex"}
            or data["version"] != 1
            or type(data["version"]) is not int
            or not isinstance(data["payload_hex"], str)
            or len(data["payload_hex"]) > 2 * MAX_ENVELOPE_BYTES
            or not isinstance(data["service_id"], str)
            or type(data["timestamp"]) is not int
            or not isinstance(data["nonce"], str)
            or not isinstance(data["signature"], str)
        ):
            raise ValueError("invalid")
        payload = bytes.fromhex(data["payload_hex"])
    except (UnicodeError, ValueError, KeyError, TypeError):
        raise BrokerTransportRejected("BROKER_FRAME_INVALID") from None
    return gate.admit(
        sock,
        payload,
        service_id=data["service_id"],
        timestamp=data["timestamp"],
        nonce=data["nonce"],
        signature=data["signature"],
    )
