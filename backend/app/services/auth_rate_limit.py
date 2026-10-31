"""Distributed fixed-window auth throttling via PostgreSQL atomic UPSERT.

No client-supplied X-Forwarded-For parsing. The ASGI server must be configured
with an explicit trusted-proxy allowlist; otherwise use the direct peer address.
Email/IP identifiers are stored as HMAC-SHA256 digests, never as plaintext.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from math import ceil

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings
from app.db.session import Database


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = max(1, retry_after)
        super().__init__("Rate limit exceeded")


class RateLimitUnavailable(Exception):
    pass


# INSERT ... ON CONFLICT serializes concurrent workers for each key.
# statement_timestamp is evaluated within PostgreSQL, avoiding worker clock skew.
_ATOMIC_INCREMENT = text("""
INSERT INTO auth_rate_limits (key_digest, window_started_at, hits)
VALUES (:key_digest, statement_timestamp(), 1)
ON CONFLICT (key_digest) DO UPDATE SET
    hits = CASE
        WHEN auth_rate_limits.window_started_at <=
             statement_timestamp() - (:seconds * INTERVAL '1 second')
        THEN 1 ELSE auth_rate_limits.hits + 1
    END,
    window_started_at = CASE
        WHEN auth_rate_limits.window_started_at <=
             statement_timestamp() - (:seconds * INTERVAL '1 second')
        THEN statement_timestamp() ELSE auth_rate_limits.window_started_at
    END
RETURNING hits, window_started_at
""")

# Expired rows are pruned occasionally, bounded to a batch to reduce lock pressure.
_PRUNE = text("""
DELETE FROM auth_rate_limits WHERE key_digest IN (
    SELECT key_digest FROM auth_rate_limits
    WHERE window_started_at < statement_timestamp() - INTERVAL '2 days'
    LIMIT 100
)
""")


def _key(settings: Settings, kind: str, identity: str) -> str:
    assert settings.auth_rate_limit_secret is not None
    secret = settings.auth_rate_limit_secret.get_secret_value().encode("utf-8")
    return hmac.new(
        secret, f"{kind}:{identity}".encode(), hashlib.sha256
    ).hexdigest()


def consume(
    database: Database,
    settings: Settings,
    *,
    kind: str,
    identity: str,
    maximum: int,
) -> None:
    """Always consumes an attempt, including failed credentials and invalid payloads.

    On DB failure, raise RateLimitUnavailable instead of silently bypassing limits.
    """
    if not settings.auth_rate_limit_enabled:
        return
    digest = _key(settings, kind, identity)
    seconds = settings.auth_limit_window_seconds
    try:
        with database.engine.begin() as connection:
            row = connection.execute(
                _ATOMIC_INCREMENT,
                {"key_digest": digest, "seconds": seconds},
            ).one()
            # Probabilistic cleanup also covers one-off, high-cardinality attacker keys.
            if secrets.randbelow(64) == 0:
                connection.execute(_PRUNE)
    except SQLAlchemyError as exc:
        raise RateLimitUnavailable from exc
    if row.hits > maximum:
        start = row.window_started_at
        if start.tzinfo is None:
            start = start.replace(tzinfo=UTC)
        deadline = start + timedelta(seconds=seconds)
        remaining = (deadline - datetime.now(UTC)).total_seconds()
        raise RateLimitExceeded(ceil(remaining))
