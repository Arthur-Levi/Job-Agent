"""F.1.2.4-C actual Unix filesystem socket & process mechanics (synthetic only).

POSITIVE tests inject a stub dispatch to prove IPC mechanics; they DO NOT
claim genuine distinct UID/HMAC transport, parser Docker or AppArmor approval.
The production-default path still requires a separate-UID gateway identity,
signed transport, full 12/12 LSM proof, and a dedicated lab VM.
"""

import multiprocessing
import os
import socket
import stat
import threading
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

from app.workers.broker_transport_wire import read_frame, send_frame
from app.workers.secops_f124b_broker_parser import SyntheticDispatchResult
from app.workers.secops_f124c_private_socket import (
    PrivateSocketRejected,
    connect_private_broker,
    open_private_broker_listener,
    read_opaque_broker_result,
    serve_one_synthetic,
)


def _private_path(tmp_path: Path) -> Path:
    root = tmp_path / "socket"
    root.mkdir(mode=0o710)
    root.chmod(0o710)
    return root / "broker.sock"


def _fake_dispatch(connection: socket.socket, *, gate: Any) -> SyntheticDispatchResult:
    """Consume the complete synthetic frame before ACK (avoid early-close race)."""
    if read_frame(connection, max_bytes=128) != b"synthetic test: stub dispatch, not authenticated":
        raise ValueError("unexpected synthetic fixture")
    return SyntheticDispatchResult("a" * 64, "txt", ("experience",), 1)


def _separate_broker_process(path: str, ready: Any, result: Any) -> None:
    try:
        listener = open_private_broker_listener(
            path, broker_uid=os.geteuid(), gateway_gid=os.getegid()
        )
        ready.set()
        try:
            ok = serve_one_synthetic(
                listener,
                broker_uid=os.geteuid(),
                gateway_uid=os.geteuid() + 1000,
                gateway_gid=os.getegid(),
                gate=Mock(),
                dispatch=_fake_dispatch,
            )
            result.put(ok)
        finally:
            listener.close()
    except BaseException:
        ready.set()
        result.put(False)


def test_real_separate_process_unix_ipc_mechanics_only(tmp_path: Path) -> None:
    path = _private_path(tmp_path)
    context = multiprocessing.get_context("fork")
    ready = context.Event()
    result = context.Queue()
    broker = context.Process(target=_separate_broker_process, args=(str(path), ready, result))
    broker.start()
    try:
        assert ready.wait(4)
        assert broker.is_alive()
        details = path.stat()
        assert stat.S_ISSOCK(details.st_mode)
        assert stat.S_IMODE(details.st_mode) == 0o660
        with connect_private_broker(str(path)) as client:
            send_frame(client, b"synthetic test: stub dispatch, not authenticated")
            assert read_opaque_broker_result(client)
        assert result.get(timeout=4) is True
        broker.join(timeout=4)
        assert broker.exitcode == 0
    finally:
        if broker.is_alive():
            broker.terminate()
            broker.join(timeout=4)
        result.close()
        result.join_thread()
        path.unlink(missing_ok=True)


def test_private_directory_required(tmp_path: Path) -> None:
    root = tmp_path / "unsafe"
    root.mkdir()
    root.chmod(0o777)
    with pytest.raises(PrivateSocketRejected):
        open_private_broker_listener(
            str(root / "broker.sock"), broker_uid=os.geteuid(), gateway_gid=os.getegid()
        )


def test_symlink_parent_is_denied(tmp_path: Path) -> None:
    source = tmp_path / "protected"
    source.mkdir(mode=0o710)
    source.chmod(0o710)
    shortcut = tmp_path / "shortcut"
    shortcut.symlink_to(source, target_is_directory=True)
    with pytest.raises(PrivateSocketRejected):
        open_private_broker_listener(
            str(shortcut / "broker.sock"), broker_uid=os.geteuid(), gateway_gid=os.getegid()
        )


def test_existing_path_refused_not_unlinked(tmp_path: Path) -> None:
    path = _private_path(tmp_path)
    path.write_bytes(b"sentinel")
    with pytest.raises(PrivateSocketRejected):
        open_private_broker_listener(str(path), broker_uid=os.geteuid(), gateway_gid=os.getegid())
    assert path.read_bytes() == b"sentinel"


def test_wrong_broker_uid_fail_closed(tmp_path: Path) -> None:
    path = _private_path(tmp_path)
    with pytest.raises(PrivateSocketRejected):
        open_private_broker_listener(
            str(path), broker_uid=os.geteuid() + 1000, gateway_gid=os.getegid()
        )
    assert not path.exists()


def test_connection_fails_without_listener(tmp_path: Path) -> None:
    path = _private_path(tmp_path)
    with pytest.raises(PrivateSocketRejected):
        connect_private_broker(str(path), timeout=0.1)


def test_listener_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = _private_path(tmp_path)
    monkeypatch.setattr("app.workers.secops_f124c_private_socket.MAX_CLIENT_SECONDS", 0.03)
    listener = open_private_broker_listener(
        str(path), broker_uid=os.geteuid(), gateway_gid=os.getegid()
    )
    try:
        with pytest.raises(PrivateSocketRejected, match="F124C_TIMEOUT"):
            serve_one_synthetic(
                listener,
                broker_uid=os.geteuid(),
                gateway_uid=os.geteuid() + 1000,
                gateway_gid=os.getegid(),
                gate=Mock(),
                dispatch=_fake_dispatch,
            )
    finally:
        listener.close()
        path.unlink()


def test_dispatch_rejection_returns_only_opaque_code(tmp_path: Path) -> None:
    path = _private_path(tmp_path)
    listener = open_private_broker_listener(
        str(path), broker_uid=os.geteuid(), gateway_gid=os.getegid()
    )
    from app.workers.secops_f124b_broker_parser import SyntheticDispatchRejected

    def rejected(connection: socket.socket, *, gate: Any) -> SyntheticDispatchResult:
        if read_frame(connection, max_bytes=128) != b"synthetic invalid request":
            raise ValueError("unexpected synthetic fixture")
        raise SyntheticDispatchRejected("PRIVATE_MESSAGE_WOULD_LEAK")

    outcomes: list[bool] = []

    def run() -> None:
        outcomes.append(
            serve_one_synthetic(
                listener,
                broker_uid=os.geteuid(),
                gateway_uid=os.geteuid() + 1000,
                gateway_gid=os.getegid(),
                gate=Mock(),
                dispatch=rejected,
            )
        )

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    try:
        with connect_private_broker(str(path)) as client:
            send_frame(client, b"synthetic invalid request")
            assert not read_opaque_broker_result(client)
        thread.join(timeout=4)
        assert not thread.is_alive()
        assert outcomes == [False]
    finally:
        listener.close()
        path.unlink(missing_ok=True)


def test_reject_same_broker_and_gateway_uid(tmp_path: Path) -> None:
    path = _private_path(tmp_path)
    listener = open_private_broker_listener(
        str(path), broker_uid=os.geteuid(), gateway_gid=os.getegid()
    )
    try:
        with pytest.raises(PrivateSocketRejected):
            serve_one_synthetic(
                listener,
                broker_uid=os.geteuid(),
                gateway_uid=os.geteuid(),
                gateway_gid=os.getegid(),
                gate=Mock(),
                dispatch=_fake_dispatch,
            )
    finally:
        listener.close()
        path.unlink()


def test_private_response_bounds(tmp_path: Path) -> None:
    left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        send_frame(left, b"A" * 70)
        with pytest.raises(PrivateSocketRejected):
            read_opaque_broker_result(right)
    finally:
        left.close()
        right.close()
