# SEC-OPS-01.E2.2-D.2 — Multiprocess and transactional recovery acceptance

**Status: CODE PUBLISHED / TESTS NOT YET EXECUTED / NO-GO.**  
Tracking: Issue #23, Draft PR #24.

## Scope

This step adds **five opt-in tests** in `backend/tests/integration/test_distributed_recovery.py` against the previously established `PostgresAdmissionStore`. Each test requires a separately provisioned and explicitly acknowledged disposable PostgreSQL database, with the schema from `backend/scripts/secops_admission_schema.sql`.

The test subprocesses use `sys.executable` and their own independent Python interpreters and PostgreSQL connections. They use only synthetic bytes and the test-only key `b"T"*32`; no Docker runtime or document parser is invoked by the test suite.

## Acceptance cases

1. **Idempotency across restarts:** process A submits; after exit, independent process B submits the same job and receives the same job ID. An independently launched process can query its state.
2. **Replay across restarts:** the same service nonce is rejected by a separate process.
3. **Global quota between processes:** six separately launched interpreters contend for one shared reservation; exactly one is admitted.
4. **Stale reservation recovery:** a deliberately backdated reservation expires during the next admission, which can then use the freed slot. The old reservation becomes `expired`.
5. **Killed in-flight transaction:** a child process obtains the advisory transaction lock and performs an uncommitted write. When it is killed, PostgreSQL must roll back the write, release the lock, and permit a subsequent admission.

**Important limitations:** expiration does not stop a running parser; there is no actual worker supervision, lease heartbeat, safe retries for uncertain execution outcomes, queue draining, durable cancellation dispatch or garbage collection. A rollback test does not prove automatic recovery of a real parser process or external side effects.

## Explicit isolation requirements

- Never set `SECOPS_DISPOSABLE_DSN` to any preserved Codespaces PostgreSQL.
- Provision a new disposable PostgreSQL instance/database named `secops_disposable_*`.
- Set `SECOPS_DISPOSABLE_ACK=I_OWN_THIS_DISPOSABLE_DB` only for that disposable database.
- Tests **TRUNCATE** only the disposable admission schema tables they are explicitly configured to use.
- A run with SKIP is **not an acceptance PASS**.
- Do not wire this experimental store into production or remove `CV_SANDBOX_REQUIRED`.

## Verification

```bash
cd backend
python -m ruff check .
python -m ruff format --check .
python -m mypy
python -m pytest tests/unit/test_job_protocol.py tests/unit/test_job_admission.py -q
# Only after schema and explicit disposable DB provision:
python -m pytest tests/integration/test_distributed_recovery.py -v
```

## Future blockers

- Evidence from an isolated disposable database, including all five new tests.
- Restart, heartbeat and fencing tests involving a real worker lease; prevent old workers continuing after lease expiration.
- Confirm distributed capacity accounting with multiple worker *hosts*, not merely local Python interpreters.
- Policy for expiration, requeue, retry, orphan detection and data retention/GC.
- Authenticated transport and end-user identity established from the actual API session.
- Privilege/isolation verification of worker host and parser runtime.
- Independent security review and blocking CI gates.

**Current SEC/OPS Gate 1 decision: NO-GO.**
