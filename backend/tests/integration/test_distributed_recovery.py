"""E2.2-D.2: opt-in process-level crash/restart and reservation recovery.

Requires an explicitly provisioned disposable PostgreSQL. No parser is started.
Tests TRUNCATE their own disposable tables: NEVER point at application databases.
"""

import json
import os
import select
import subprocess
import sys
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest

ACK = "I_OWN_THIS_DISPOSABLE_DB"
KEY = b"T" * 32
ROOT = Path(__file__).resolve().parents[2]

# Independent child processes: no shared in-memory Python service or semaphore.
CHILD = """
import base64
import json
import os
import sys
import time
from uuid import uuid4
from app.workers.distributed_admission import PostgresAdmissionStore
from app.workers.job_admission import AdmissionRejected, AdmissionService

message = json.loads(sys.stdin.buffer.read())
owner = message["owner"]
body = {
    "version": 1,
    "operation": message["operation"],
    "request_id": str(uuid4()),
    "subject": {"user_id": owner, "tenant_id": message.get("tenant", "test_tenant")},
}
if message["operation"] == "submit":
    body["idempotency_key"] = message["idem"]
    body["payload"] = {
        "filename": "synthetic.txt",
        "content_b64": base64.b64encode(b"synthetic only").decode(),
    }
else:
    body["job_id"] = message["job_id"]
raw = json.dumps(body).encode()
key = b"T" * 32
service = AdmissionService(
    {"api": key},
    PostgresAdmissionStore(
        os.environ["SECOPS_DISPOSABLE_DSN"],
        global_limit=int(message.get("global_limit", 2)),
        user_limit=int(message.get("user_limit", 1)),
    ),
)
timestamp = int(time.time())
nonce = message.get("nonce", uuid4().hex)
try:
    result = service.admit(
        raw,
        service_id="api",
        timestamp=timestamp,
        nonce=nonce,
        signature=AdmissionService.signature(key, raw, timestamp, nonce),
    )
    print(json.dumps({
        "outcome": "ADMITTED",
        "job_id": str(result.job_id),
        "status": result.status,
        "reused": result.reused,
    }))
except AdmissionRejected as exc:
    print(json.dumps({"outcome": exc.code}))
"""


@pytest.fixture()
def disposable_dsn() -> Iterator[str]:
    dsn = os.getenv("SECOPS_DISPOSABLE_DSN", "")
    if not dsn or os.getenv("SECOPS_DISPOSABLE_ACK") != ACK:
        pytest.skip("Disposable SEC/OPS DB not explicitly configured")
    parsed = psycopg.conninfo.conninfo_to_dict(dsn)
    if not str(parsed.get("dbname", "")).startswith("secops_disposable_"):
        pytest.fail("Refusing a non-disposable database name")
    with psycopg.connect(dsn, connect_timeout=3) as conn, conn.cursor() as cur:
        cur.execute("TRUNCATE secops_admission.nonces, secops_admission.jobs")
    yield dsn


def child_env(dsn: str) -> dict[str, str]:
    # Never pass application DATABASE_URL to the test child.
    env = os.environ.copy()
    env.pop("DATABASE_URL", None)
    env["SECOPS_DISPOSABLE_DSN"] = dsn
    return env


def launch(dsn: str) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [sys.executable, "-c", CHILD],
        cwd=ROOT,
        env=child_env(dsn),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def collect(process: subprocess.Popen[bytes], message: dict[str, object]) -> dict[str, object]:
    encoded = json.dumps(message).encode("utf-8")
    try:
        stdout, stderr = process.communicate(input=encoded, timeout=20)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        pytest.fail("Child process timed out")
    assert process.returncode == 0, stderr.decode(errors="replace")[-1500:]
    return json.loads(stdout)


def run_child(dsn: str, message: dict[str, object]) -> dict[str, object]:
    return collect(launch(dsn), message)


def test_separate_processes_share_idempotency_after_restart(disposable_dsn: str) -> None:
    owner = str(uuid4())
    command = {"operation": "submit", "owner": owner, "idem": "once"}
    first = run_child(disposable_dsn, command)
    second = run_child(disposable_dsn, command)
    assert first["outcome"] == second["outcome"] == "ADMITTED"
    assert second["job_id"] == first["job_id"]
    assert first["reused"] is False
    assert second["reused"] is True

    status = run_child(
        disposable_dsn,
        {"operation": "status", "owner": owner, "job_id": first["job_id"]},
    )
    assert status["status"] == "queued"


def test_nonce_replay_survives_process_restart(disposable_dsn: str) -> None:
    owner = str(uuid4())
    nonce = uuid4().hex
    first = run_child(
        disposable_dsn,
        {"operation": "submit", "owner": owner, "idem": "replay", "nonce": nonce},
    )
    assert first["outcome"] == "ADMITTED"
    second = run_child(
        disposable_dsn,
        {"operation": "submit", "owner": owner, "idem": "replay", "nonce": nonce},
    )
    assert second["outcome"] == "ADMISSION_REPLAY"


def test_quota_with_six_real_processes(disposable_dsn: str) -> None:
    processes = [launch(disposable_dsn) for _ in range(6)]
    try:
        commands = [
            {"operation": "submit", "owner": str(uuid4()), "idem": f"parallel_{n}",
             "global_limit": 1}
            for n in range(6)
        ]
        with ThreadPoolExecutor(max_workers=6) as pool:
            outputs = list(pool.map(lambda pair: collect(*pair), zip(processes, commands)))
        assert sum(item["outcome"] == "ADMITTED" for item in outputs) == 1
        assert sum(item["outcome"] == "ADMISSION_BUSY" for item in outputs) == 5
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.communicate()


def test_expired_reservation_recovered_on_next_admission(disposable_dsn: str) -> None:
    owner = str(uuid4())
    first = run_child(
        disposable_dsn,
        {"operation": "submit", "owner": owner, "idem": "old", "global_limit": 1},
    )
    assert first["outcome"] == "ADMITTED"
    # Synthetic stale record only. Does NOT kill an actual parser process.
    with psycopg.connect(disposable_dsn, connect_timeout=3) as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE secops_admission.jobs SET expires_at = now() - interval '1 second' "
            "WHERE job_id = %s",
            (first["job_id"],),
        )
    replacement = run_child(
        disposable_dsn,
        {"operation": "submit", "owner": str(uuid4()), "idem": "new", "global_limit": 1},
    )
    assert replacement["outcome"] == "ADMITTED"
    old = run_child(
        disposable_dsn,
        {"operation": "status", "owner": owner, "job_id": first["job_id"]},
    )
    assert old["status"] == "expired"


def test_killed_transaction_rolls_back_and_releases_advisory_lock(
    disposable_dsn: str,
) -> None:
    marker = uuid4().hex
    blocker = """
import os
import psycopg
with psycopg.connect(os.environ["SECOPS_DISPOSABLE_DSN"], connect_timeout=3) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(18427, 1)")
        cur.execute(
            "INSERT INTO secops_admission.nonces (service_id, nonce, expires_at) "
            "VALUES ('rollback_test', %s, now() + interval '120 seconds')",
            (os.environ["SECOPS_TEST_MARKER"],),
        )
        print("LOCKED", flush=True)
        import time
        time.sleep(30)
"""
    env = child_env(disposable_dsn)
    env["SECOPS_TEST_MARKER"] = marker
    process = subprocess.Popen(
        [sys.executable, "-c", blocker],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        assert process.stdout is not None
        readable, _, _ = select.select([process.stdout], [], [], 10)
        assert readable, "Child did not acquire lock before deadline"
        assert process.stdout.readline().strip() == b"LOCKED"
    finally:
        process.kill()
        process.communicate(timeout=5)

    with psycopg.connect(disposable_dsn, connect_timeout=3) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM secops_admission.nonces "
            "WHERE service_id = 'rollback_test' AND nonce = %s",
            (marker,),
        )
        assert cur.fetchone() == (0,)

    result = run_child(
        disposable_dsn,
        {"operation": "submit", "owner": str(uuid4()), "idem": "post_crash"},
    )
    assert result["outcome"] == "ADMITTED"
