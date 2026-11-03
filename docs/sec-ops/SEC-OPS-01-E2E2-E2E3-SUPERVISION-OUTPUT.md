# SEC/OPS E2.2-E.2 and E2.2-E.3 — Experimental acceptance

**Status: CODE CANDIDATE / NOT ACCEPTED / PRODUCTION NO-GO**. Issue #23; Draft PR #24.

## E2.2-E.2: synthetic supervisor

`backend/app/workers/synthetic_supervisor.py`:
- Executes **only reviewed fixed synthetic Python code**, selected from two allowed modes (`exit`, `sleep`).
- No shell, CV bytes, job input, parser invocation or network listener.
- Checks lease ownership before starting and repeatedly during execution. Database heartbeat exception is treated as revocation (fail closed).
- Uses a private POSIX process session, bounded timeout, SIGTERM then SIGKILL, without collecting stdout/stderr.
- Calls fenced `finish` only after process exit; failed terminal authorization is reported as revocation.
- Unit tests cover success, pre-launch revocation, running revocation and timeout.

**Gaps:** no real worker container/VM isolation, process-tree supervision beyond POSIX process group, OS resource quotas, kill acknowledgement for detached grandchildren, signal-safe runtime shutdown or host-level orchestrator. No guarantee against effects outside the process group. Not a secure untrusted-file execution boundary.

## E2.2-E.3: digest-only fenced publication

`backend/app/workers/protected_output.py`:
- Accepts at most 65536 bytes of **synthetic result data** for hashing; **does not persist those bytes**.
- Under the same PostgreSQL advisory transaction lock, verifies current job state and lease owner, generation and deadline.
- Commits one record in disposable-only `secops_admission.publications` (SHA-256 digest, size and owner metadata) **and** terminal `succeeded` job status in one transaction.
- Identical duplicate publication from the exact same worker/generation is idempotent. Changed data, owner or generation conflicts fail closed.
- Tests cover success, replay, conflict, stale generation, cancelled job and oversize data.

**Critical distinction:** no actual result output is published to a destination. This proves only metadata fencing. A real output path still needs transactional fencing at the final storage destination or an outbox/commit protocol with object integrity, scope, retention, cleanup, and process termination; otherwise old workers could write output despite a revoked lease.

## Safety and validation

Schema is restricted to independently provisioned disposable PostgreSQL, not Alembic or app DB. Never supply any existing Codespaces DB as `SECOPS_DISPOSABLE_DSN`.

```bash
cd /workspaces/Job-Agent-SEC-OPS-01
bash backend/scripts/secops_disposable_recovery.sh
source .venv-secops/bin/activate
cd backend
python -m pytest tests/unit/test_synthetic_supervisor.py -q
python -m ruff check .
python -m ruff format --check .
python -m mypy
```

Expected: 21 opt-in PostgreSQL tests (6 + 5 + 5 + 5), plus five new synthetic supervisor unit tests. These are targets, not pre-confirmed results. CI passing without disposable DB does not count as integration acceptance.

Blockers before actual CV parsing:
1. Production API session-derived user identity, workload identity, authenticated TLS/mTLS and granular authorization.
2. Separate secured worker host and constrained parser runtime, hardened against hostile documents, with independent security review.
3. Actual process orchestration and proven termination of old workers; no concurrent untrusted parser side effects.
4. Real staged output storage with immutable object, fenced commit, retrieval authorization, retention and GC.
5. Timeouts, crash recovery, operator metrics/alerts, retries/poison queue and end-to-end threat tests.

**Retain `CV_SANDBOX_REQUIRED`. SEC/OPS Gate 1 remains NO-GO.**
