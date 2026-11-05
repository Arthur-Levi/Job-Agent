"""F.1.2.4-C private one-shot Unix socket broker transport (synthetic lab only).

This adapter is not imported by any public API or production worker. The server
must run as the *real* designated broker UID and the caller as a distinct
registered gateway UID. Its parser dispatch remains fail-closed unless actual
12/12 LSM runtime attestation succeeds. No network listener or real CVs.
"""

import contextlib
import os
import socket
import stat
from collections.abc import Callable
from pathlib import Path

from app.workers.broker_transport_auth import BrokerTransportGate, BrokerTransportRejected
from app.workers.broker_transport_wire import read_frame, send_frame
from app.workers.secops_f124b_broker_parser import (
    SyntheticDispatchRejected,
    SyntheticDispatchResult,
    dispatch_synthetic_authenticated,
)

MAX_SOCKET_PATH = 100
MAX_CLIENT_SECONDS = 3.0
# This is a compact, opaque response; the parser's output is never written.
_DENIED = b"F124C_DENIED"


class PrivateSocketRejected(Exception):
    def __init__(self, code: str = "F124C_DENIED") -> None:
        self.code = code
        super().__init__(code)


def _private_directory(path: Path) -> None:
    """Require a pre-existing broker-owned directory with no symlink traversal."""
    if not path.is_absolute() or path.is_symlink():
        raise PrivateSocketRejected()
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid():
        raise PrivateSocketRejected()
    # 0710 grants traversal to gateway group, not directory listing. The socket
    # itself must separately grant group write (0660).
    if stat.S_IMODE(info.st_mode) not in {0o700, 0o710}:
        raise PrivateSocketRejected()


def open_private_broker_listener(path: str, *, broker_uid: int, gateway_gid: int) -> socket.socket:
    """Bind once; never unlink a pre-existing socket, path or symlink.

    A distinct gateway UID and a broker-owned 0710 directory with group set to
    the gateway's group are required if the gateway must connect to the socket.
    """
    if (
        os.name != "posix"
        or os.geteuid() != broker_uid
        or broker_uid <= 0
        or gateway_gid < 0
        or not path.startswith("/")
        or len(os.fsencode(path)) > MAX_SOCKET_PATH
    ):
        raise PrivateSocketRejected()
    target = Path(path)
    parent = target.parent
    _private_directory(parent)
    parent_info = parent.stat()
    if parent_info.st_gid != gateway_gid and stat.S_IMODE(parent_info.st_mode) != 0o700:
        raise PrivateSocketRejected()
    # A 0700 parent is only useful for same-UID testing and cannot grant an
    # independently identified gateway access: reject operationally.
    if stat.S_IMODE(parent_info.st_mode) != 0o710:
        raise PrivateSocketRejected()
    if target.exists() or target.is_symlink():
        raise PrivateSocketRejected()
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        # Group ownership of socket is inherited from directory's setgid bit
        # only in some setups; explicitly chown the socket after binding.
        old_umask = os.umask(0o117)
        try:
            listener.bind(path)
        finally:
            os.umask(old_umask)
        os.chown(path, broker_uid, gateway_gid)
        os.chmod(path, 0o660)
        details = target.lstat()
        if (
            not stat.S_ISSOCK(details.st_mode)
            or details.st_uid != broker_uid
            or details.st_gid != gateway_gid
            or stat.S_IMODE(details.st_mode) != 0o660
        ):
            raise PrivateSocketRejected()
        listener.listen(2)
        listener.settimeout(MAX_CLIENT_SECONDS)
        return listener
    except (OSError, PrivateSocketRejected):
        listener.close()
        # No other actor should be able to replace this broker-owned pathname
        # in its 0710 protected directory.
        try:
            if target.is_socket() and target.lstat().st_uid == broker_uid:
                target.unlink()
        except OSError:
            pass
        raise PrivateSocketRejected() from None


def serve_one_synthetic(
    listener: socket.socket,
    *,
    broker_uid: int,
    gateway_uid: int,
    gateway_gid: int,
    gate: BrokerTransportGate,
    dispatch: Callable[..., SyntheticDispatchResult] = dispatch_synthetic_authenticated,
) -> bool:
    """One bounded accepted request; return success without exposing parsed CV text.

    Runtime identity verification does not trust the client's claimed JSON UID.
    Injected dispatch is test-only; the default requires effective 12/12 proof.
    """
    if (
        os.geteuid() != broker_uid
        or broker_uid <= 0
        or gateway_uid <= 0
        or broker_uid == gateway_uid
        or gateway_gid < 0
        or listener.family != socket.AF_UNIX
    ):
        raise PrivateSocketRejected()
    try:
        connection, _ = listener.accept()
    except (OSError, TimeoutError):
        raise PrivateSocketRejected("F124C_TIMEOUT") from None
    with connection:
        connection.settimeout(MAX_CLIENT_SECONDS)
        try:
            # The admission gate validates the actual SO_PEERCRED again.
            result = dispatch(connection, gate=gate)
            if not isinstance(result, SyntheticDispatchResult):
                raise PrivateSocketRejected()
            send_frame(connection, b"F124C_ACCEPTED")
            return True
        except (OSError, TimeoutError, BrokerTransportRejected, SyntheticDispatchRejected):
            with contextlib.suppress(OSError, BrokerTransportRejected):
                send_frame(connection, _DENIED)
            return False
        except PrivateSocketRejected:
            with contextlib.suppress(OSError, BrokerTransportRejected):
                send_frame(connection, _DENIED)
            return False


def connect_private_broker(path: str, *, timeout: float = MAX_CLIENT_SECONDS) -> socket.socket:
    """Client-side private socket connection, never a TCP/public endpoint."""
    if not path.startswith("/") or len(os.fsencode(path)) > MAX_SOCKET_PATH:
        raise PrivateSocketRejected()
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        client.settimeout(timeout)
        client.connect(path)
        return client
    except OSError:
        client.close()
        raise PrivateSocketRejected() from None


def read_opaque_broker_result(connection: socket.socket) -> bool:
    """Opaque success code only; frame is bounded before allocation."""
    try:
        response = read_frame(connection, max_bytes=64)
    except (OSError, BrokerTransportRejected):
        raise PrivateSocketRejected() from None
    if response == b"F124C_ACCEPTED":
        return True
    if response == _DENIED:
        return False
    raise PrivateSocketRejected()
