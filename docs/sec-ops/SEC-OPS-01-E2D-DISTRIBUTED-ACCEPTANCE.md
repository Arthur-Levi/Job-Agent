# SEC-OPS E2.2-D — PostgreSQL distributed admission (experimental)

**Status: IMPLEMENTATION CANDIDATE / NOT APPROVED / NO-GO.**
Tracked by Issue #23 and Draft PR #24.

## What exists

- `backend/app/workers/distributed_admission.py`: `PostgresAdmissionStore` implementing the same store interface used by the signed in-memory admission prototype.
- `backend/scripts/secops_admission_schema.sql`: explicit DDL, **never** run automatically or added to existing Alembic migrations.
- `backend/tests/integration/test_distributed_admission.py`: opt-in tests for two independent store objects and six concurrent submissions. All fixtures are synthetic.

Transaction boundaries:
- Each submission uses a **fixed PostgreSQL advisory transaction lock** and the same database to serialize quota counting and insertions. This is deliberately coarse, and may become a throughput bottleneck.
- Idempotency is keyed by `(tenant_id, user_id, idem_key)`, backed by a database uniqueness constraint; conflicts compare a digest of synthetic input.
- Nonces are uniquely keyed by `(service_id, nonce)` with expiry, independent of process restarts. They are admitted in a **separate transaction** from the associated job; a failed job admission consumes its nonce, but does not create a job.
- `status` / `cancel` require matching owner and tenant, and cancellation releases its quota reservation atomically.
- Expired `queued/running` reservations are marked expired under the same lock; **this does not terminate any running parser**. No parser is connected.
- **No CV bytes are persisted.** Fingerprints, job identity, and status are persisted. Retention and garbage collection of job metadata remain unimplemented.
- Connections require an explicit DSN. There is no production wiring, no endpoint and no automatic fallback to in-memory admission.

## Opt-in tests: disposable PostgreSQL only

Do not use `DATABASE_URL` or any of the preserved Codespaces DBs. Provision a **new dedicated database** named `secops_disposable_*` on a genuinely disposable PostgreSQL instance (preferably CI service container/ephemeral VM). Execute the standalone schema script *only there*:

```bash
# Example run ONLY after independently provisioning a disposable PostgreSQL.
# Never paste a real secret into the repository or CI logs.
export SECOPS_DISPOSABLE_DSN='postgresql://<test-user>:<secret>@<test-host>/<secops_disposable_test>'
export SECOPS_DISPOSABLE_ACK=I_OWN_THIS_DISPOSABLE_DB
psql "$SECOPS_DISPOSABLE_DSN" -v ON_ERROR_STOP=1 -f backend/scripts/secops_admission_schema.sql
cd backend
python -m pytest tests/integration/test_distributed_admission.py -q
```

Tests will **SKIP** unless both variables exist and the database's parsed name starts with `secops_disposable_`. The test fixture runs TRUNCATE on the specified database: **the explicit acknowledgement is a destructive-test opt-in**, not an authorization guarantee. Never set this acknowledgement for an existing database.

Normal local/CI checks (no database access):

```bash
cd backend
python -m pytest tests/unit/test_job_protocol.py tests/unit/test_job_admission.py -q
python -m ruff check app/workers/distributed_admission.py tests/integration/test_distributed_admission.py
python -m ruff format --check app/workers/distributed_admission.py tests/integration/test_distributed_admission.py
python -m mypy
```

## Known blockers

1. Distributed integration tests have **not** yet been demonstrated against a freshly provisioned, truly isolated PostgreSQL instance.
2. Operationally provisioned worker-host identity, authenticated remote transport, service identity rotation/revocation and TLS/mTLS still do not exist.
3. HMAC authenticates the configured API workload only; a client-supplied `subject` is **not** an authorization proof. Real API session integration and per-operation authorization are pending.
4. Fixed global advisory lock may impair throughput; performance, lock timeouts and multi-replica crash behavior need soak tests.
5. Heartbeats/leases, actual process cancellation, metadata retention policy, cleanup/GC, worker supervision and distributed capacity reconciliation are pending.
6. No actual parser execution or production API integration is allowed at this phase.
7. A passing CI without the explicit disposable DSN means **integration tests were skipped**, not passed.

**Production decision remains NO-GO. Keep `CV_SANDBOX_REQUIRED` active.**
