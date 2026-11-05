"""E2.2-F.1.2.1: atomic durable nonce ledger for a disposable broker lab.

Never use in production without audited storage provisioning, backup and
retention, multi-instance concurrency, key rotation, and tenant authorization.
"""

import os
import sqlite3
import stat
from contextlib import closing
from pathlib import Path


class SqliteBrokerReplayStore:
    """Durable replay defense; each accept_nonce transaction is atomic.

    The file must live inside a private, broker-owned 0700 directory. Reopening
    the store (including after a process restart) preserves accepted nonces.
    """

    def __init__(self, filename: str) -> None:
        target = Path(filename)
        parent = target.parent
        if (
            not target.is_absolute()
            or target.is_symlink()
            or not parent.is_dir()
            or stat.S_IMODE(parent.stat().st_mode) != 0o700
            or parent.stat().st_uid != os.geteuid()
        ):
            raise ValueError("replay DB requires a broker-owned 0700 directory")
        self._path = filename
        try:
            with closing(self._connect()) as conn:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS seen_nonces("
                    "service_id TEXT NOT NULL, nonce TEXT NOT NULL, "
                    "expires_at INTEGER NOT NULL, PRIMARY KEY(service_id, nonce))"
                )
            if stat.S_IMODE(target.stat().st_mode) & 0o077:
                raise ValueError("replay DB permissions must be private")
        except sqlite3.Error as exc:
            raise RuntimeError("BROKER_REPLAY_STORE_UNAVAILABLE") from exc

    def _connect(self) -> sqlite3.Connection:
        # SQLite creates the file respecting the current process umask.
        # The broker process must use umask 077 before initializing the store.
        conn = sqlite3.connect(self._path, timeout=2, isolation_level=None)
        conn.execute("PRAGMA busy_timeout=2000")
        return conn

    def accept_nonce(self, service_id: str, nonce: str, now: int) -> bool:
        """Atomic insert-or-reject; fail closed if database is inaccessible."""
        try:
            with self._connect() as conn:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute("DELETE FROM seen_nonces WHERE expires_at < ?", (now,))
                cursor = conn.execute(
                    "INSERT OR IGNORE INTO seen_nonces(service_id,nonce,expires_at) VALUES (?,?,?)",
                    (service_id, nonce, now + 120),
                )
                conn.execute("COMMIT")
                return cursor.rowcount == 1
        except sqlite3.Error as exc:
            raise RuntimeError("BROKER_REPLAY_STORE_UNAVAILABLE") from exc
