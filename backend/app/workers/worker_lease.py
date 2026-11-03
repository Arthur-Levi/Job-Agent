"""Experimental DB-backed worker leases; NO parser, transport or API integration.

Generation fencing prevents a superseded worker from changing DB job state.
It does NOT prevent external side effects of a stale parser; that requires
worker-process termination and fencing at the actual output destination.
"""

from dataclasses import dataclass
from uuid import UUID

import psycopg

from app.workers.job_admission import AdmissionRejected

_LOCK_NAMESPACE = 18427
_LOCK_KEY = 1


@dataclass(frozen=True)
class WorkerLease:
    job_id: UUID
    worker_id: UUID
    generation: int


class WorkerLeaseStore:
    """Atomic claim, heartbeat and completion against disposable PostgreSQL.

    No fallback to memory. Lease time is calculated by PostgreSQL, avoiding
    different worker host clocks. All writes require a current fencing token.
    """

    def __init__(self, dsn: str, *, lease_seconds: int = 30) -> None:
        if not dsn or not 5 <= lease_seconds <= 300:
            raise ValueError("invalid worker lease configuration")
        self._dsn = dsn
        self._ttl = lease_seconds

    @staticmethod
    def _lock(cur: psycopg.Cursor[tuple[object, ...]]) -> None:
        # Same lock as admission store, so cancellation and expiration serialize.
        cur.execute("SELECT pg_advisory_xact_lock(%s, %s)", (_LOCK_NAMESPACE, _LOCK_KEY))

    def claim(self, worker_id: UUID) -> WorkerLease | None:
        """Claim queued work or recover an expired running lease, atomically."""
        if worker_id.int == 0:
            raise ValueError("worker_id must not be nil")
        try:
            with psycopg.connect(self._dsn, connect_timeout=3) as conn, conn.cursor() as cur:
                self._lock(cur)
                cur.execute(
                    """
                    SELECT j.job_id
                    FROM secops_admission.jobs AS j
                    LEFT JOIN secops_admission.leases AS l ON l.job_id = j.job_id
                    WHERE j.expires_at > now()
                      AND (
                        (j.status = 'queued' AND l.job_id IS NULL)
                        OR (j.status = 'running' AND l.deadline <= now())
                      )
                    ORDER BY j.expires_at, j.job_id
                    LIMIT 1
                    FOR UPDATE OF j SKIP LOCKED
                    """
                )
                row = cur.fetchone()
                if row is None:
                    return None
                job_id = row[0]
                cur.execute(
                    """
                    INSERT INTO secops_admission.leases
                        (job_id, worker_id, generation, deadline)
                    VALUES (%s, %s, 1, now() + (%s * interval '1 second'))
                    ON CONFLICT (job_id) DO UPDATE
                    SET worker_id = EXCLUDED.worker_id,
                        generation = secops_admission.leases.generation + 1,
                        deadline = EXCLUDED.deadline
                    RETURNING generation
                    """,
                    (job_id, worker_id, self._ttl),
                )
                generation = cur.fetchone()
                if generation is None:
                    raise AdmissionRejected("LEASE_UNAVAILABLE")
                cur.execute(
                    """
                    UPDATE secops_admission.jobs
                    SET status = 'running',
                        expires_at = greatest(expires_at, now() +
                            (%s * interval '1 second') + interval '30 seconds')
                    WHERE job_id = %s AND status IN ('queued', 'running')
                    """,
                    (self._ttl, job_id),
                )
                if cur.rowcount != 1:
                    raise AdmissionRejected("LEASE_CONFLICT")
                return WorkerLease(job_id, worker_id, int(generation[0]))
        except psycopg.Error:
            raise AdmissionRejected("LEASE_UNAVAILABLE") from None

    def heartbeat(self, lease: WorkerLease) -> bool:
        """Renew only if generation/owner still current and lease not expired."""
        try:
            with psycopg.connect(self._dsn, connect_timeout=3) as conn, conn.cursor() as cur:
                self._lock(cur)
                cur.execute(
                    """
                    UPDATE secops_admission.leases AS l
                    SET deadline = now() + (%s * interval '1 second')
                    FROM secops_admission.jobs AS j
                    WHERE l.job_id = %s AND l.worker_id = %s
                      AND l.generation = %s AND l.deadline > now()
                      AND j.job_id = l.job_id AND j.status = 'running'
                      AND j.expires_at > now()
                    RETURNING l.job_id
                    """,
                    (self._ttl, lease.job_id, lease.worker_id, lease.generation),
                )
                if cur.fetchone() is None:
                    return False
                cur.execute(
                    """
                    UPDATE secops_admission.jobs
                    SET expires_at = greatest(expires_at, now() +
                        (%s * interval '1 second') + interval '30 seconds')
                    WHERE job_id = %s AND status = 'running'
                    """,
                    (self._ttl, lease.job_id),
                )
                return cur.rowcount == 1
        except psycopg.Error:
            raise AdmissionRejected("LEASE_UNAVAILABLE") from None

    def finish(self, lease: WorkerLease, *, succeeded: bool) -> bool:
        """Fenced terminal transition; stale/expired owners cannot finish."""
        try:
            with psycopg.connect(self._dsn, connect_timeout=3) as conn, conn.cursor() as cur:
                self._lock(cur)
                cur.execute(
                    """
                    UPDATE secops_admission.jobs AS j
                    SET status = %s
                    FROM secops_admission.leases AS l
                    WHERE j.job_id = %s AND j.status = 'running'
                      AND j.expires_at > now()
                      AND l.job_id = j.job_id AND l.worker_id = %s
                      AND l.generation = %s AND l.deadline > now()
                    RETURNING j.job_id
                    """,
                    (
                        "succeeded" if succeeded else "failed",
                        lease.job_id,
                        lease.worker_id,
                        lease.generation,
                    ),
                )
                return cur.fetchone() is not None
        except psycopg.Error:
            raise AdmissionRejected("LEASE_UNAVAILABLE") from None
