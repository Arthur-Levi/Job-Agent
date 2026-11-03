"""Experimental PostgreSQL admission store: NO Docker, parser, or API integration.

Requires separately initialized tables in a disposable test database.
Every operation uses an independent transaction. A fixed advisory transaction
lock serializes quota checks across *all* replicas sharing this same database.
This is a coarse proof of correctness, NOT a scalable production queue.
"""

import hashlib
import hmac
import time
from collections.abc import Callable
from uuid import uuid4

import psycopg

from app.workers.job_admission import (
    AdmissionRejected,
    AdmissionResult,
)
from app.workers.job_protocol import ValidatedJob

# Fixed lock namespace for all participating replicas of this store.
_LOCK_NAMESPACE = 18427
_LOCK_KEY = 1
_ACTIVE = ("queued", "running")


class PostgresAdmissionStore:
    """Transactional quotas and idempotency; no resume bytes stored.

    The supplied DSN MUST point to an explicitly provisioned disposable
    SEC/OPS database during tests. Never accepts the app DATABASE_URL by default.
    """

    def __init__(
        self,
        dsn: str,
        *,
        global_limit: int = 2,
        user_limit: int = 1,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if not dsn or global_limit < 1 or user_limit < 1:
            raise ValueError("invalid admission store configuration")
        self._dsn = dsn
        self._global_limit = global_limit
        self._user_limit = user_limit
        self._clock = clock

    def accept_nonce(self, service_id: str, nonce: str, now: int) -> bool:
        """Globally unique nonce within expiry window, including across restarts."""
        try:
            with psycopg.connect(self._dsn, connect_timeout=3) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM secops_admission.nonces WHERE expires_at < now()"
                    )
                    cursor.execute(
                        """
                        INSERT INTO secops_admission.nonces
                            (service_id, nonce, expires_at)
                        VALUES (%s, %s, now() + interval '120 seconds')
                        ON CONFLICT DO NOTHING RETURNING nonce
                        """,
                        (service_id, nonce),
                    )
                    return cursor.fetchone() is not None
        except psycopg.Error:
            raise AdmissionRejected("ADMISSION_UNAVAILABLE") from None

    def submit(self, job: ValidatedJob) -> AdmissionResult:
        if job.operation != "submit" or job.idempotency_key is None:
            raise AdmissionRejected("ADMISSION_INVALID")
        if job.document is None or job.filename is None:
            raise AdmissionRejected("ADMISSION_INVALID")
        fingerprint = hashlib.sha256(
            job.filename.encode("utf-8") + b"\x00" + hashlib.sha256(job.document).digest()
        ).digest()
        try:
            with psycopg.connect(self._dsn, connect_timeout=3) as conn:
                with conn.cursor() as cursor:
                    # A single global lock serializes idempotency and quota checks.
                    cursor.execute(
                        "SELECT pg_advisory_xact_lock(%s, %s)",
                        (_LOCK_NAMESPACE, _LOCK_KEY),
                    )
                    self._expire_jobs(cursor)
                    cursor.execute(
                        """
                        SELECT job_id, fingerprint, status
                        FROM secops_admission.jobs
                        WHERE tenant_id = %s AND user_id = %s AND idem_key = %s
                        """,
                        (job.tenant_id, job.user_id, job.idempotency_key),
                    )
                    previous = cursor.fetchone()
                    if previous is not None:
                        prior_id, prior_fingerprint, prior_status = previous
                        if not hmac.compare_digest(bytes(prior_fingerprint), fingerprint):
                            raise AdmissionRejected("ADMISSION_CONFLICT")
                        return AdmissionResult(prior_id, prior_status, reused=True)
                    cursor.execute(
                        """
                        SELECT count(*)
                        FROM secops_admission.jobs
                        WHERE status IN ('queued', 'running')
                        """
                    )
                    total_row = cursor.fetchone()
                    if total_row is None or int(total_row[0]) >= self._global_limit:
                        raise AdmissionRejected("ADMISSION_BUSY")
                    cursor.execute(
                        """
                        SELECT count(*)
                        FROM secops_admission.jobs
                        WHERE status IN ('queued', 'running')
                          AND tenant_id = %s AND user_id = %s
                        """,
                        (job.tenant_id, job.user_id),
                    )
                    user_row = cursor.fetchone()
                    if user_row is None or int(user_row[0]) >= self._user_limit:
                        raise AdmissionRejected("ADMISSION_BUSY")
                    job_id = uuid4()
                    cursor.execute(
                        """
                        INSERT INTO secops_admission.jobs
                            (job_id, tenant_id, user_id, idem_key, fingerprint, status)
                        VALUES (%s, %s, %s, %s, %s, 'queued')
                        """,
                        (job_id, job.tenant_id, job.user_id, job.idempotency_key, fingerprint),
                    )
                    return AdmissionResult(job_id, "queued")
        except psycopg.Error:
            raise AdmissionRejected("ADMISSION_UNAVAILABLE") from None

    def inspect(self, job: ValidatedJob) -> AdmissionResult:
        if job.job_id is None:
            raise AdmissionRejected("ADMISSION_INVALID")
        try:
            with psycopg.connect(self._dsn, connect_timeout=3) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT pg_advisory_xact_lock(%s, %s)",
                        (_LOCK_NAMESPACE, _LOCK_KEY),
                    )
                    self._expire_jobs(cursor)
                    cursor.execute(
                        """
                        SELECT status FROM secops_admission.jobs
                        WHERE job_id = %s AND tenant_id = %s AND user_id = %s
                        """,
                        (job.job_id, job.tenant_id, job.user_id),
                    )
                    row = cursor.fetchone()
                    if row is None:
                        raise AdmissionRejected("ADMISSION_NOT_FOUND")
                    status = str(row[0])
                    if job.operation == "cancel" and status in _ACTIVE:
                        cursor.execute(
                            """
                            UPDATE secops_admission.jobs
                            SET status = 'cancelled'
                            WHERE job_id = %s
                            """,
                            (job.job_id,),
                        )
                        status = "cancelled"
                    return AdmissionResult(job.job_id, status)
        except psycopg.Error:
            raise AdmissionRejected("ADMISSION_UNAVAILABLE") from None

    @staticmethod
    def _expire_jobs(cursor: psycopg.Cursor[tuple[object, ...]]) -> None:
        # Expired reservations no longer consume quota. Existing idempotency
        # keys remain retained; explicit garbage collection requires separate policy.
        cursor.execute(
            """
            UPDATE secops_admission.jobs
            SET status = 'expired'
            WHERE status IN ('queued', 'running') AND expires_at <= now()
            """
        )
