"""Opt-in synthetic digest publication tests; no CV or parser execution."""

import hashlib
import os
from uuid import UUID, uuid4

import psycopg
import pytest

from app.workers.job_admission import AdmissionRejected
from app.workers.protected_output import ProtectedOutputStore
from app.workers.worker_lease import WorkerLeaseStore


@pytest.fixture()
def dsn() -> str:
    dsn = os.getenv("SECOPS_DISPOSABLE_DSN", "")
    if not dsn or os.getenv("SECOPS_DISPOSABLE_ACK") != "I_OWN_THIS_DISPOSABLE_DB":
        pytest.skip("Disposable SEC/OPS PostgreSQL only")
    info = psycopg.conninfo.conninfo_to_dict(dsn)
    if not str(info.get("dbname", "")).startswith("secops_disposable_"):
        pytest.fail("Refusing persistent DB")
    with psycopg.connect(dsn, connect_timeout=3) as conn, conn.cursor() as cur:
        cur.execute(
            "TRUNCATE secops_admission.nonces, secops_admission.publications, "
            "secops_admission.leases, secops_admission.jobs"
        )
    return dsn


def enqueue(dsn: str) -> UUID:
    job_id = uuid4()
    with psycopg.connect(dsn, connect_timeout=3) as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO secops_admission.jobs
                (job_id, tenant_id, user_id, idem_key, fingerprint, status)
            VALUES (%s, 'synthetic', %s, %s, %s, 'queued')
            """,
            (job_id, uuid4(), uuid4().hex, b"synthetic"),
        )
    return job_id


def test_publish_is_atomic_and_reusable(dsn: str) -> None:
    job_id = enqueue(dsn)
    lease = WorkerLeaseStore(dsn).claim(uuid4())
    assert lease is not None and lease.job_id == job_id
    data = b"synthetic-result"
    first = ProtectedOutputStore(dsn).publish(lease, data)
    assert first.digest == hashlib.sha256(data).digest()
    assert first.byte_count == len(data)
    assert not first.reused
    second = ProtectedOutputStore(dsn).publish(lease, data)
    assert second.reused
    with psycopg.connect(dsn, connect_timeout=3) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT status FROM secops_admission.jobs WHERE job_id = %s",
            (job_id,),
        )
        assert cur.fetchone() == ("succeeded",)
        cur.execute(
            "SELECT count(*) FROM secops_admission.publications WHERE job_id = %s",
            (job_id,),
        )
        assert cur.fetchone() == (1,)


def test_conflicting_second_publication_rejected(dsn: str) -> None:
    enqueue(dsn)
    lease = WorkerLeaseStore(dsn).claim(uuid4())
    assert lease is not None
    store = ProtectedOutputStore(dsn)
    store.publish(lease, b"first")
    with pytest.raises(AdmissionRejected, match="OUTPUT_CONFLICT"):
        store.publish(lease, b"second")


def test_stale_worker_cannot_publish_after_takeover(dsn: str) -> None:
    enqueue(dsn)
    lease_store = WorkerLeaseStore(dsn)
    old = lease_store.claim(uuid4())
    assert old is not None
    with psycopg.connect(dsn, connect_timeout=3) as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE secops_admission.leases SET deadline = now() - interval '1 second' "
            "WHERE job_id = %s",
            (old.job_id,),
        )
    current = lease_store.claim(uuid4())
    assert current is not None and current.generation == old.generation + 1
    publisher = ProtectedOutputStore(dsn)
    with pytest.raises(AdmissionRejected, match="OUTPUT_FENCED"):
        publisher.publish(old, b"stale")
    current_result = publisher.publish(current, b"current")
    assert not current_result.reused
    with pytest.raises(AdmissionRejected, match="OUTPUT_CONFLICT"):
        publisher.publish(old, b"stale")


def test_cancelled_job_cannot_publish(dsn: str) -> None:
    enqueue(dsn)
    lease = WorkerLeaseStore(dsn).claim(uuid4())
    assert lease is not None
    with psycopg.connect(dsn, connect_timeout=3) as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE secops_admission.jobs SET status = 'cancelled' WHERE job_id = %s",
            (lease.job_id,),
        )
    with pytest.raises(AdmissionRejected, match="OUTPUT_FENCED"):
        ProtectedOutputStore(dsn).publish(lease, b"result")
    with psycopg.connect(dsn, connect_timeout=3) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM secops_admission.publications WHERE job_id = %s",
            (lease.job_id,),
        )
        assert cur.fetchone() == (0,)


def test_oversize_output_fails_closed(dsn: str) -> None:
    enqueue(dsn)
    lease = WorkerLeaseStore(dsn).claim(uuid4())
    assert lease is not None
    with pytest.raises(AdmissionRejected, match="OUTPUT_INVALID"):
        ProtectedOutputStore(dsn).publish(lease, b"x" * 65537)
