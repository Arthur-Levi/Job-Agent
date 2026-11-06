"""Metadata-only, fenced synthetic output publication.

This does NOT persist or expose CV/parser output bytes. It proves an atomic
authorization boundary for a digest; external object storage fencing is still
required before real output is safe. Production integration is forbidden.
"""

import hashlib
import hmac
from dataclasses import dataclass

import psycopg

from app.workers.job_admission import AdmissionRejected
from app.workers.worker_lease import WorkerLease, WorkerLeaseStore

MAX_SYNTHETIC_OUTPUT = 65536


@dataclass(frozen=True)
class Publication:
    digest: bytes
    byte_count: int
    reused: bool = False


class ProtectedOutputStore:
    """Publish digest and terminal job state in one fenced PostgreSQL transaction."""

    def __init__(self, dsn: str) -> None:
        if not dsn:
            raise ValueError("dsn required")
        self._dsn = dsn

    def publish(self, lease: WorkerLease, data: bytes) -> Publication:
        if not isinstance(data, bytes) or not 0 < len(data) <= MAX_SYNTHETIC_OUTPUT:
            raise AdmissionRejected("OUTPUT_INVALID")
        digest = hashlib.sha256(data).digest()
        try:
            with psycopg.connect(self._dsn, connect_timeout=3) as conn, conn.cursor() as cur:
                WorkerLeaseStore._lock(cur)
                # Idempotent duplicate only for the exact worker, generation and data.
                cur.execute(
                    """
                    SELECT worker_id, generation, digest, byte_count
                    FROM secops_admission.publications
                    WHERE job_id = %s
                    """,
                    (lease.job_id,),
                )
                previous = cur.fetchone()
                if previous is not None:
                    owner, generation, earlier_digest, size = previous
                    if (
                        owner == lease.worker_id
                        and generation == lease.generation
                        and int(size) == len(data)
                        and hmac.compare_digest(bytes(earlier_digest), digest)
                    ):
                        return Publication(digest, len(data), reused=True)
                    raise AdmissionRejected("OUTPUT_CONFLICT")

                cur.execute(
                    """
                    SELECT 1
                    FROM secops_admission.jobs AS j
                    JOIN secops_admission.leases AS l ON l.job_id = j.job_id
                    WHERE j.job_id = %s AND j.status = 'running'
                      AND j.expires_at > now()
                      AND l.worker_id = %s AND l.generation = %s
                      AND l.deadline > now()
                    FOR UPDATE OF j
                    """,
                    (lease.job_id, lease.worker_id, lease.generation),
                )
                if cur.fetchone() is None:
                    raise AdmissionRejected("OUTPUT_FENCED")
                cur.execute(
                    """
                    INSERT INTO secops_admission.publications
                        (job_id, worker_id, generation, digest, byte_count)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (lease.job_id, lease.worker_id, lease.generation, digest, len(data)),
                )
                cur.execute(
                    """
                    UPDATE secops_admission.jobs SET status = 'succeeded'
                    WHERE job_id = %s AND status = 'running'
                    """,
                    (lease.job_id,),
                )
                if cur.rowcount != 1:
                    raise AdmissionRejected("OUTPUT_FENCED")
                return Publication(digest, len(data))
        except psycopg.Error:
            raise AdmissionRejected("OUTPUT_UNAVAILABLE") from None
