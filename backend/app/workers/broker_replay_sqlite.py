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
        # Pre-create the file with a restrictive mode instead of relying on
        # the process umask or the SQLite library's default creation mode.
        # Fail closed for pre-existing world/group-accessible files.
        try:
            flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            try:
                descriptor = os.open(filename, flags, 0o600)
            except FileExistsError:
                if target.is_symlink():
                    raise ValueError("replay DB requires a regular private file") from None
            else:
                os.close(descriptor)
            file_info = target.stat()
            if (
                not stat.S_ISREG(file_info.st_mode)
                or file_info.st_uid != os.geteuid()
                or stat.S_IMODE(file_info.st_mode) != 0o600
            ):
                raise ValueError("replay DB requires a broker-owned 0600 regular file")
        except OSError as exc:
            raise RuntimeError("BROKER_REPLAY_STORE_UNAVAILABLE") from exc

        self._path = filename
        try:
            with closing(self._connect()) as conn:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS seen_nonces("
                    "service_id TEXT NOT NULL, nonce TEXT NOT NULL, "
                    "expires_at INTEGER NOT NULL, PRIMARY KEY(service_id, nonce))"
                )
        except sqlite3.Error as exc:
            raise RuntimeError("BROKER_REPLAY_STORE_UNAVAILABLE") from exc

    def _connect(self) -> sqlite3.Connection:
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
