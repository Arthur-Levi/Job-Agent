"""Disposable broker replay persistence tests: no customer data or real services."""

import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from app.workers.broker_replay_sqlite import SqliteBrokerReplayStore


def private_store(directory: Path) -> SqliteBrokerReplayStore:
    directory.mkdir(mode=0o700)
    db = directory / "nonces.sqlite3"
    prior = os.umask(0o077)
    try:
        return SqliteBrokerReplayStore(str(db))
    finally:
        os.umask(prior)


def test_nonce_replay_survives_new_store_instance(tmp_path: Path) -> None:
    path = tmp_path / "broker-private"
    first = private_store(path)
    assert first.accept_nonce("broker:gateway", "a" * 32, 1000)
    assert not SqliteBrokerReplayStore(str(path / "nonces.sqlite3")).accept_nonce(
        "broker:gateway", "a" * 32, 1001
    )
    assert SqliteBrokerReplayStore(str(path / "nonces.sqlite3")).accept_nonce(
        "broker:gateway", "b" * 32, 1001
    )


def test_atomic_single_winner_concurrent_connections(tmp_path: Path) -> None:
    path = tmp_path / "broker-private"
    store = private_store(path)
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _: store.accept_nonce("gw", "x" * 32, 1000), range(8)))
    assert results.count(True) == 1
    assert results.count(False) == 7


def test_expiration_after_window(tmp_path: Path) -> None:
    store = private_store(tmp_path / "broker-private")
    assert store.accept_nonce("gw", "z" * 32, 1000)
    assert not store.accept_nonce("gw", "z" * 32, 1120)
    assert store.accept_nonce("gw", "z" * 32, 1121)


def test_rejects_nonprivate_directory(tmp_path: Path) -> None:
    directory = tmp_path / "public"
    directory.mkdir(mode=0o755)
    with pytest.raises(ValueError, match="broker-owned"):
        SqliteBrokerReplayStore(str(directory / "db.sqlite"))


def test_corrupt_database_fails_closed(tmp_path: Path) -> None:
    directory = tmp_path / "broker-private"
    directory.mkdir(mode=0o700)
    db = directory / "nonces.sqlite3"
    db.write_bytes(b"not a sqlite database")
    os.chmod(db, 0o600)
    with pytest.raises(RuntimeError, match="UNAVAILABLE"):
        SqliteBrokerReplayStore(str(db))


def test_reject_symlink_database(tmp_path: Path) -> None:
    directory = tmp_path / "broker-private"
    directory.mkdir(mode=0o700)
    target = tmp_path / "other"
    target.write_bytes(b"dummy")
    (directory / "nonces.sqlite3").symlink_to(target)
    with pytest.raises(ValueError, match="broker-owned"):
        SqliteBrokerReplayStore(str(directory / "nonces.sqlite3"))


def test_unavailable_store_cannot_accept(tmp_path: Path) -> None:
    directory = tmp_path / "broker-private"
    store = private_store(directory)
    with sqlite3.connect(directory / "nonces.sqlite3") as connection:
        connection.execute("DROP TABLE seen_nonces")
    with pytest.raises(RuntimeError, match="UNAVAILABLE"):
        store.accept_nonce("gw", "a" * 32, 1000)
