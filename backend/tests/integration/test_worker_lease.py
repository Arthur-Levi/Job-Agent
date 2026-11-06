"""Opt-in disposable DB acceptance for worker leases; never starts a parser."""

import os
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import psycopg
import pytest

from app.workers.worker_lease import WorkerLeaseStore

ACK = "I_OWN_THIS_DISPOSABLE_DB"


@pytest.fixture()
def dsn() -> str:
    value = os.getenv("SECOPS_DISPOSABLE_DSN", "")
    if not value or os.getenv("SECOPS_DISPOSABLE_ACK") != ACK:
        pytest.skip("Explicit disposable PostgreSQL required")
    parsed = psycopg.conninfo.conninfo_to_dict(value)
    if not str(parsed.get("dbname", "")).startswith("secops_disposable_"):
        pytest.fail("Refusing a non-disposable database")
    with psycopg.connect(value, connect_timeout=3) as conn, conn.cursor() as cur:
        cur.execute(
            "TRUNCATE secops_admission.nonces, secops_admission.publications, "
            "secops_admission.leases, secops_admission.jobs"
        )
    return value


def enqueue(dsn: str) -> UUID:
    job_id = uuid4()
    with psycopg.connect(dsn, connect_timeout=3) as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO secops_admission.jobs
                (job_id, tenant_id, user_id, idem_key, fingerprint, status)
            VALUES (%s, 'test_tenant', %s, %s, %s, 'queued')
            """,
            (job_id, uuid4(), uuid4().hex, b"synthetic-fingerprint"),
        )
    return job_id


def status(dsn: str, job_id: UUID) -> str:
    with psycopg.connect(dsn, connect_timeout=3) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT status FROM secops_admission.jobs WHERE job_id = %s",
            (job_id,),
        )
        row = cur.fetchone()
        assert row is not None
        return str(row[0])


def test_only_one_worker_claims_a_job(dsn: str) -> None:
    job_id = enqueue(dsn)
    store = WorkerLeaseStore(dsn)
    first = store.claim(uuid4())
    assert first is not None and first.job_id == job_id
    assert first.generation == 1
    assert store.claim(uuid4()) is None
    assert status(dsn, job_id) == "running"


def test_heartbeat_and_fenced_completion(dsn: str) -> None:
    job_id = enqueue(dsn)
    lease = WorkerLeaseStore(dsn).claim(uuid4())
    assert lease is not None
    other = WorkerLeaseStore(dsn)
    assert other.heartbeat(lease)
    assert other.finish(lease, succeeded=True)
    assert status(dsn, job_id) == "succeeded"
    assert not other.heartbeat(lease)
    assert not other.finish(lease, succeeded=True)


def test_expired_lease_takeover_fences_old_worker(dsn: str) -> None:
    job_id = enqueue(dsn)
    store = WorkerLeaseStore(dsn)
    old = store.claim(uuid4())
    assert old is not None
    with psycopg.connect(dsn, connect_timeout=3) as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE secops_admission.leases
            SET deadline = now() - interval '1 second'
            WHERE job_id = %s
            """,
            (job_id,),
        )
    new = WorkerLeaseStore(dsn).claim(uuid4())
    assert new is not None
    assert new.job_id == job_id
    assert new.generation == old.generation + 1
    assert new.worker_id != old.worker_id
    assert not store.heartbeat(old)
    assert not store.finish(old, succeeded=True)
    assert WorkerLeaseStore(dsn).finish(new, succeeded=False)
    assert status(dsn, job_id) == "failed"


def test_cancelled_job_rejects_worker_updates(dsn: str) -> None:
    job_id = enqueue(dsn)
    store = WorkerLeaseStore(dsn)
    lease = store.claim(uuid4())
    assert lease is not None
    with psycopg.connect(dsn, connect_timeout=3) as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE secops_admission.jobs SET status = 'cancelled' WHERE job_id = %s",
            (job_id,),
        )
    assert not store.heartbeat(lease)
    assert not store.finish(lease, succeeded=True)
    assert store.claim(uuid4()) is None


def test_concurrent_claims_are_exclusive(dsn: str) -> None:
    job_id = enqueue(dsn)
    worker_ids = [uuid4() for _ in range(6)]

    def attempt(worker_id: UUID) -> bool:
        result = WorkerLeaseStore(dsn).claim(worker_id)
        return result is not None and result.job_id == job_id

    with ThreadPoolExecutor(max_workers=6) as pool:
        claimed = list(pool.map(attempt, worker_ids))
    assert claimed.count(True) == 1
    assert claimed.count(False) == 5
