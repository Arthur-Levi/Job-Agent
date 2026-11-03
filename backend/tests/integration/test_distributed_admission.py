"""Opt-in PostgreSQL integration checks; requires an explicitly disposable DB.

No Docker, migrations, parser, or production DATABASE_URL is used here.
Set SECOPS_DISPOSABLE_DSN to an isolated test database URL and
SECOPS_DISPOSABLE_ACK=I_OWN_THIS_DISPOSABLE_DB to enable tests.
Schema must already be initialized using scripts/secops_admission_schema.sql.
"""

import base64
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import psycopg
import pytest

from app.workers.distributed_admission import PostgresAdmissionStore
from app.workers.job_admission import AdmissionRejected, AdmissionResult, AdmissionService

KEY = b"T" * 32
ACK = "I_OWN_THIS_DISPOSABLE_DB"


@pytest.fixture()
def dsn() -> str:
    value = os.getenv("SECOPS_DISPOSABLE_DSN", "")
    if not value or os.getenv("SECOPS_DISPOSABLE_ACK") != ACK:
        pytest.skip("Disposable SEC/OPS DB not explicitly configured")
    # Never trust DATABASE_URL or existing application databases.
    info = psycopg.conninfo.conninfo_to_dict(value)
    database = str(info.get("dbname", ""))
    if not database.startswith("secops_disposable_"):
        pytest.fail("Refusing a database not named secops_disposable_*")
    return value


@pytest.fixture()
def reset_tables(dsn: str) -> str:
    with psycopg.connect(dsn, connect_timeout=3) as conn, conn.cursor() as cursor:
        cursor.execute(
            "TRUNCATE secops_admission.nonces, secops_admission.leases, secops_admission.jobs"
        )
    return dsn


def envelope(
    user_id: str,
    *,
    tenant_id: str = "test_tenant",
    idem: str = "same_key",
    content: bytes = b"synthetic job",
    operation: str = "submit",
    job_id: str | None = None,
) -> bytes:
    value: dict[str, object] = {
        "version": 1,
        "operation": operation,
        "request_id": str(uuid4()),
        "subject": {"user_id": user_id, "tenant_id": tenant_id},
    }
    if operation == "submit":
        value["idempotency_key"] = idem
        value["payload"] = {
            "filename": "synthetic.txt",
            "content_b64": base64.b64encode(content).decode(),
        }
    else:
        value["job_id"] = job_id
    return json.dumps(value).encode("utf-8")


def build(dsn: str, *, global_limit: int = 2, user_limit: int = 1) -> AdmissionService:
    return AdmissionService(
        {"api": KEY},
        PostgresAdmissionStore(dsn, global_limit=global_limit, user_limit=user_limit),
    )


def send(service: AdmissionService, value: bytes) -> AdmissionResult:
    timestamp = int(time.time())
    nonce = uuid4().hex
    return service.admit(
        value,
        service_id="api",
        timestamp=timestamp,
        nonce=nonce,
        signature=AdmissionService.signature(KEY, value, timestamp, nonce),
    )


def test_two_store_instances_share_idempotency(reset_tables: str) -> None:
    first_service = build(reset_tables)
    second_service = build(reset_tables)
    user = str(uuid4())
    first = send(first_service, envelope(user))
    second = send(second_service, envelope(user))
    assert first.job_id == second.job_id
    assert second.reused is True


def test_replay_protection_shared_between_stores(reset_tables: str) -> None:
    first_service = build(reset_tables)
    second_service = build(reset_tables)
    user = str(uuid4())
    value = envelope(user)
    timestamp = int(time.time())
    nonce = uuid4().hex
    signature = AdmissionService.signature(KEY, value, timestamp, nonce)
    first_service.admit(
        value, service_id="api", timestamp=timestamp, nonce=nonce, signature=signature
    )
    with pytest.raises(AdmissionRejected, match="ADMISSION_REPLAY"):
        second_service.admit(
            value, service_id="api", timestamp=timestamp, nonce=nonce, signature=signature
        )


def test_global_quota_across_concurrent_instances(reset_tables: str) -> None:
    services = [build(reset_tables, global_limit=1) for _ in range(6)]

    def attempt(index: int) -> str:
        try:
            send(services[index], envelope(str(uuid4()), idem=str(index)))
        except AdmissionRejected as exc:
            return exc.code
        return "ADMITTED"

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(attempt, range(6)))
    assert results.count("ADMITTED") == 1
    assert results.count("ADMISSION_BUSY") == 5


def test_owner_isolation_and_cancel_releases_capacity(reset_tables: str) -> None:
    service = build(reset_tables, global_limit=1)
    owner = str(uuid4())
    first = send(service, envelope(owner))
    other = str(uuid4())
    with pytest.raises(AdmissionRejected, match="ADMISSION_NOT_FOUND"):
        send(
            build(reset_tables),
            envelope(other, operation="cancel", job_id=str(first.job_id)),
        )
    cancelled = send(
        service,
        envelope(
            owner,
            operation="cancel",
            job_id=str(first.job_id),
        ),
    )
    assert cancelled.status == "cancelled"
    next_job = send(build(reset_tables, global_limit=1), envelope(other))
    assert next_job.status == "queued"


def test_idempotency_conflict_is_shared(reset_tables: str) -> None:
    user = str(uuid4())
    send(build(reset_tables), envelope(user))
    with pytest.raises(AdmissionRejected, match="ADMISSION_CONFLICT"):
        send(build(reset_tables), envelope(user, content=b"different synthetic bytes"))


def test_missing_schema_fails_closed(dsn: str) -> None:
    # No unsafe schema mutation: the separate test intentionally checks that
    # the store never falls back to an in-process memory quota.
    store = PostgresAdmissionStore("postgresql://invalid-host.invalid/fake")
    with pytest.raises(AdmissionRejected, match="ADMISSION_UNAVAILABLE"):
        store.accept_nonce("api", uuid4().hex, 1)
