"""E2.2-F.1.2.4-D: fail-closed real-identity boundary for synthetic broker lab.

No API import, no standalone listener, no privilege switching, no real CVs.
The only accepted success route calls the F124B dispatcher WITHOUT injected
attestor or executor: both kernel LSM attestation and the actual Docker parser
must succeed. Codespaces with unconfined AppArmor remains NO-GO.
"""

import os
import socket
import stat
from pathlib import Path

from app.workers.broker_transport_auth import BrokerTransportGate, GatewayWorkload
from app.workers.gateway_identity import GatewayIdentityGate
from app.workers.secops_f124b_broker_parser import (
    SyntheticDispatchRejected,
    dispatch_synthetic_authenticated,
)
from app.workers.secops_f124c_private_socket import (
    PrivateSocketRejected,
    serve_one_synthetic,
)


class RuntimeIdentityRejected(Exception):
    """No raw peer metadata, socket paths or document contents in exceptions."""

    def __init__(self) -> None:
        super().__init__("F124D_IDENTITY_UNVERIFIED")


def verify_broker_identity(
    listener: socket.socket,
    *,
    path: str,
    broker_uid: int,
    gateway: GatewayWorkload,
) -> None:
    """Check actual process and socket ownership before accepting a connection.

    The broker MUST be a distinct non-root OS identity. Directory and socket
    cannot grant access to world/other users. This check does not certify that
    the gateway has no independent Docker credentials on its host.
    """
    if (
        type(broker_uid) is not int
        or type(gateway.uid) is not int
        or type(gateway.gid) is not int
        or broker_uid <= 0
        or gateway.uid <= 0
        or gateway.gid < 0
        or broker_uid == gateway.uid
        or os.geteuid() != broker_uid
        or listener.family != socket.AF_UNIX
    ):
        raise RuntimeIdentityRejected()
    try:
        target = Path(path)
        parent = target.parent
        if not target.is_absolute() or target.is_symlink() or parent.is_symlink():
            raise RuntimeIdentityRejected()
        if listener.getsockname() != str(target):
            raise RuntimeIdentityRejected()
        if listener.getsockopt(socket.SOL_SOCKET, socket.SO_ACCEPTCONN) != 1:
            raise RuntimeIdentityRejected()
        directory = parent.lstat()
        endpoint = target.lstat()
        if (
            not stat.S_ISDIR(directory.st_mode)
            or directory.st_uid != broker_uid
            or directory.st_gid != gateway.gid
            or stat.S_IMODE(directory.st_mode) != 0o710
            or not stat.S_ISSOCK(endpoint.st_mode)
            or endpoint.st_uid != broker_uid
            or endpoint.st_gid != gateway.gid
            or stat.S_IMODE(endpoint.st_mode) != 0o660
        ):
            raise RuntimeIdentityRejected()
    except (OSError, ValueError, TypeError):
        raise RuntimeIdentityRejected() from None


def verify_gateway_peer(
    connection: socket.socket, *, broker_uid: int, gateway: GatewayWorkload
) -> None:
    """Use Linux SO_PEERCRED, never request-body/header-supplied identities."""
    if (
        broker_uid <= 0
        or gateway.uid <= 0
        or gateway.uid == broker_uid
        or len(gateway.key) < 32
        or connection.family != socket.AF_UNIX
    ):
        raise RuntimeIdentityRejected()
    try:
        observed = GatewayIdentityGate.peer_identity(connection)
    except Exception:
        raise RuntimeIdentityRejected() from None
    if observed != (gateway.uid, gateway.gid):
        raise RuntimeIdentityRejected()


def serve_one_verified_synthetic(
    listener: socket.socket,
    *,
    path: str,
    broker_uid: int,
    gateway: GatewayWorkload,
    gate: BrokerTransportGate,
) -> bool:
    """Real socket identity + signed transport + **real** isolated parser path.

    No executor/attestation dependency injection is exposed at this boundary.
    Authentication must precede the parser's runtime LSM check and execution.
    Without the VM's enforced LSM, this returns False rather than invoking a
    parser. F124C handles bounded socket timeouts and opaque failure replies.
    """
    verify_broker_identity(listener, path=path, broker_uid=broker_uid, gateway=gateway)

    def verified_dispatch(connection: socket.socket, *, gate: BrokerTransportGate) -> object:
        try:
            verify_gateway_peer(connection, broker_uid=broker_uid, gateway=gateway)
        except RuntimeIdentityRejected:
            raise SyntheticDispatchRejected() from None
        return dispatch_synthetic_authenticated(connection, gate=gate)

    try:
        return serve_one_synthetic(
            listener,
            broker_uid=broker_uid,
            gateway_uid=gateway.uid,
            gateway_gid=gateway.gid,
            gate=gate,
            dispatch=verified_dispatch,
        )
    except PrivateSocketRejected:
        raise RuntimeIdentityRejected() from None
