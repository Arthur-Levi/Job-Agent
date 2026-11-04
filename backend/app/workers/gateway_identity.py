"""SEC/OPS E2.2-F.1: synthetic-only Unix peer + service credential admission.

This is a gate prototype, NOT a listening gateway and NOT a parser path.
SO_PEERCRED binds process identity; HMAC binds the message; durable replay
protection is delegated to the configured AdmissionService store.
End-user authorization MUST be established by the API, not this module.
"""

import os
import socket
import struct
from dataclasses import dataclass

from app.workers.job_admission import AdmissionRejected, AdmissionResult, AdmissionService


@dataclass(frozen=True)
class AuthorizedWorkload:
    service_id: str
    uid: int
    gid: int


class GatewayIdentityGate:
    """Refuse clients whose OS identity is not the registered API workload."""

    def __init__(
        self,
        authorized: tuple[AuthorizedWorkload, ...],
        admission: AdmissionService,
        *,
        broker_uid: int,
    ) -> None:
        if (
            broker_uid < 1
            or not authorized
            or len({entry.service_id for entry in authorized}) != len(authorized)
            or any(
                not entry.service_id
                or entry.uid < 1
                or entry.gid < 1
                or entry.uid == broker_uid
                for entry in authorized
            )
        ):
            raise ValueError("invalid, ambiguous or unseparated workload identities")
        self._identities = {entry.service_id: entry for entry in authorized}
        self._admission = admission

    @staticmethod
    def peer_identity(sock: socket.socket) -> tuple[int, int]:
        """Linux SO_PEERCRED result, never a user-supplied header or JSON field."""
        if os.name != "posix" or not hasattr(socket, "SO_PEERCRED"):
            raise AdmissionRejected("GATEWAY_UNSUPPORTED")
        try:
            raw = sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
            _pid, uid, gid = struct.unpack("3i", raw)
        except (OSError, ValueError, struct.error):
            raise AdmissionRejected("GATEWAY_UNAUTHORIZED") from None
        return uid, gid

    def admit(
        self,
        sock: socket.socket,
        raw: bytes,
        *,
        service_id: str,
        timestamp: int,
        nonce: str,
        signature: str,
    ) -> AdmissionResult:
        authorized = self._identities.get(service_id)
        if authorized is None or (authorized.uid, authorized.gid) != self.peer_identity(sock):
            raise AdmissionRejected("GATEWAY_UNAUTHORIZED")
        # The admission service validates the HMAC, time window, message shape,
        # replay and subject-scoped store. The API must bind subject from its
        # authenticated user session BEFORE constructing/sending the envelope.
        return self._admission.admit(
            raw,
            service_id=service_id,
            timestamp=timestamp,
            nonce=nonce,
            signature=signature,
        )
