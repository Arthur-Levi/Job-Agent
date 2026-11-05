"""F124D negative-by-default real Unix identity tests; synthetic-only, no Docker.

A positive three-identity broker/parser acceptance is intentionally NOT
simulated. Its PASS requires a separate VM with a real confined parser.
"""

import os
import socket
import threading
from pathlib import Path
from unittest.mock import Mock

import pytest

from app.workers.broker_transport_auth import GatewayWorkload
from app.workers.secops_f124c_private_socket import (
    connect_private_broker,
    open_private_broker_listener,
    read_opaque_broker_result,
)
from app.workers.secops_f124d_verified_chain import (
    RuntimeIdentityRejected,
    serve_one_verified_synthetic,
    verify_broker_identity,
    verify_gateway_peer,
)


def _gateway(uid: int | None = None, gid: int | None = None) -> GatewayWorkload:
    return GatewayWorkload(
        service_id="f124d-synthetic-only",
        uid=os.geteuid() + 1000 if uid is None else uid,
        gid=os.getegid() if gid is None else gid,
        key=b"synthetic-transport-only-never-use-in-production-000",
    )


def _listener(tmp_path: Path) -> tuple[str, socket.socket]:
    parent = tmp_path / "private"
    parent.mkdir(mode=0o710)
    parent.chmod(0o710)
    path = str(parent / "broker.sock")
    listener = open_private_broker_listener(path, broker_uid=os.geteuid(), gateway_gid=os.getegid())
    return path, listener


def test_identity_attestation_accepts_actual_private_socket_structure(tmp_path: Path) -> None:
    path, listener = _listener(tmp_path)
    try:
        verify_broker_identity(listener, path=path, broker_uid=os.geteuid(), gateway=_gateway())
    finally:
        listener.close()
        Path(path).unlink()


def test_same_uid_gateway_is_forbidden(tmp_path: Path) -> None:
    path, listener = _listener(tmp_path)
    try:
        with pytest.raises(RuntimeIdentityRejected):
            verify_broker_identity(
                listener,
                path=path,
                broker_uid=os.geteuid(),
                gateway=_gateway(uid=os.geteuid()),
            )
    finally:
        listener.close()
        Path(path).unlink()


def test_false_broker_uid_is_forbidden(tmp_path: Path) -> None:
    path, listener = _listener(tmp_path)
    try:
        with pytest.raises(RuntimeIdentityRejected):
            verify_broker_identity(
                listener,
                path=path,
                broker_uid=os.geteuid() + 1001,
                gateway=_gateway(),
            )
    finally:
        listener.close()
        Path(path).unlink()


def test_socket_path_must_match_bound_listener(tmp_path: Path) -> None:
    path, listener = _listener(tmp_path)
    try:
        with pytest.raises(RuntimeIdentityRejected):
            verify_broker_identity(
                listener,
                path=path + "-different",
                broker_uid=os.geteuid(),
                gateway=_gateway(),
            )
    finally:
        listener.close()
        Path(path).unlink()


def test_socket_mode_tampering_is_denied(tmp_path: Path) -> None:
    path, listener = _listener(tmp_path)
    try:
        os.chmod(path, 0o666)
        with pytest.raises(RuntimeIdentityRejected):
            verify_broker_identity(listener, path=path, broker_uid=os.geteuid(), gateway=_gateway())
    finally:
        listener.close()
        Path(path).unlink()


def test_directory_mode_tampering_is_denied(tmp_path: Path) -> None:
    path, listener = _listener(tmp_path)
    try:
        Path(path).parent.chmod(0o777)
        with pytest.raises(RuntimeIdentityRejected):
            verify_broker_identity(listener, path=path, broker_uid=os.geteuid(), gateway=_gateway())
    finally:
        listener.close()
        Path(path).unlink()


def test_actual_linux_peer_credential_matches_only_real_uid() -> None:
    client, broker = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        verify_gateway_peer(
            broker,
            broker_uid=os.geteuid() + 1000,
            gateway=_gateway(uid=os.geteuid()),
        )
        with pytest.raises(RuntimeIdentityRejected):
            verify_gateway_peer(broker, broker_uid=os.geteuid(), gateway=_gateway())
    finally:
        client.close()
        broker.close()


def test_different_group_is_denied_even_for_correct_uid() -> None:
    client, broker = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        with pytest.raises(RuntimeIdentityRejected):
            verify_gateway_peer(
                broker,
                broker_uid=os.geteuid() + 1000,
                gateway=_gateway(uid=os.geteuid(), gid=os.getegid() + 1000),
            )
    finally:
        client.close()
        broker.close()


def test_full_verified_entrypoint_rejects_untrusted_local_peer(tmp_path: Path) -> None:
    path, listener = _listener(tmp_path)
    # The actual client is our local UID, NOT the distinct registered gateway.
    # The real verified path must refuse before any parser/attestor invocation.
    outcomes: list[bool] = []

    def broker() -> None:
        outcomes.append(
            serve_one_verified_synthetic(
                listener,
                path=path,
                broker_uid=os.geteuid(),
                gateway=_gateway(),
                gate=Mock(),
            )
        )

    thread = threading.Thread(target=broker, daemon=True)
    thread.start()
    try:
        with connect_private_broker(path) as client:
            assert not read_opaque_broker_result(client)
        thread.join(timeout=4)
        assert not thread.is_alive()
        assert outcomes == [False]
    finally:
        listener.close()
        Path(path).unlink(missing_ok=True)


def test_missing_socket_is_denied_without_dispatch(tmp_path: Path) -> None:
    path, listener = _listener(tmp_path)
    try:
        Path(path).unlink()
        with pytest.raises(RuntimeIdentityRejected):
            verify_broker_identity(listener, path=path, broker_uid=os.geteuid(), gateway=_gateway())
    finally:
        listener.close()
