# SEC/OPS E2.2-E — Worker lease and fencing prototype

**Status:** implementation published, acceptance PENDING, production **NO-GO**.

## Implemented (PostgreSQL only)

- `backend/app/workers/worker_lease.py` implements `WorkerLeaseStore` with atomic `claim`, `heartbeat`, and fenced `finish`.
- The disposable-only schema adds `secops_admission.leases` with `job_id`, `worker_id`, monotonic `generation` and database-clock `deadline`.
- A shared PostgreSQL advisory transaction lock (18427,1) serializes lease transitions with existing admission/cancellation transitions.
- Expired **lease** can be reclaimed by a different worker, which increments the generation. The prior owner is then denied DB heartbeat and completion. Terminal/cancelled/expired job states cannot be overwritten by lease completion.
- PostgreSQL connection failure raises `AdmissionRejected("LEASE_UNAVAILABLE")` (fail closed). No parser bytes, commands, images or CV data are processed.
- The tests are opt-in, synthetic and reset the disposable DB tables, including the new lease table.

## Acceptance

Run **only** after reviewing that Docker is available and the PostgreSQL 16 Alpine image is already present:

```bash
cd /workspaces/Job-Agent-SEC-OPS-01
bash backend/scripts/secops_disposable_recovery.sh
```

Expected 16 tests total (6 admission + 5 process/recovery + 5 lease tests); also run Ruff check/format, full MyPy, unit tests and CI. A skipped suite does NOT count as acceptance.

## Security limitations — non-negotiable

**Fencing in PostgreSQL does not fence a running parser's external side effects.**
A crashed, paused or partitioned worker might still be executing when its lease expires and another worker claims the job. A production execution system must isolate/terminate the prior process, fence writes to output storage, and design safe retries/idempotent finalization before requeueing. Therefore the present implementation is a coordination prototype, **not** evidence of at-most-once real parser execution.

This prototype deliberately does **not**:
- launch, parse, store or execute untrusted resumes;
- expose network listeners or integrate with production API/broker;
- implement worker host identity or authenticated control transport;
- support heartbeats/cancellation that actually kill parser processes;
- implement durable encrypted job payload handoff and cleanup;
- enforce lease progress outside database, lease fairness, maximum attempts, backoff or dead-letter;
- demonstrate production metrics, alerting, operator recovery or worker host separation.

The existing `jobs.expires_at` reservation timeout is independent from the new lease timeout. Live worker heartbeats extend the reservation, but deployment needs a single, explicit transition policy for lost workers and reservations.

Retain `CV_SANDBOX_REQUIRED`, Issue #23 **NO-GO**, and Draft PR #24. Do not copy these new tables into the production Alembic chain.
