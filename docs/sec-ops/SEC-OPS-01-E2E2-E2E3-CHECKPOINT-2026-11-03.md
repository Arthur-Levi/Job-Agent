# Job Agent — SEC/OPS checkpoint 2026-11-03

**Branch:** `feature/sec-ops-01-broker-isolation`  
**PR:** #24 (Draft) · **Issue:** #23 (security gate, NO-GO)  
**Production:** `503 CV_SANDBOX_REQUIRED` preserved. No real CV parsing authorized.

## Evidence recorded

The user ran the verification on the SEC/OPS Codespaces worktree and reported the following results **before the formatting-only checkpoint commit**:

| Check | Observed result |
|---|---|
| Unit tests: protocol + admission + synthetic supervisor | **47 passed**, 1 non-blocking `StarletteDeprecationWarning` |
| Ruff lint | **PASS**, exit 0 |
| Ruff format | **FAIL**, exit 1: one line wrap in `tests/unit/test_synthetic_supervisor.py` (line 64) |
| MyPy full project | **PASS**, 147 source files |
| Git working tree | clean and synchronized with remote at time of reported run |

**Fix committed:** `9b99a18f72858055a86a72d7d85c042d0c352df8` (`style(sec-ops): normalize negative supervisor test formatting`). Only the requested line break/comma in the test was changed. **Revalidation of Ruff format and full CI after that commit was not yet confirmed when this checkpoint was authored.**

Earlier confirmed evidence:
- E2.2-D.2: **11/11** disposable PostgreSQL integration tests (admission + processes/recovery).
- E2.2-E.1: **16/16** disposable PostgreSQL tests (adds leases); PostgreSQL cleanup routine was triggered.
- The **new** E2.2-E.3 digest-only publication integration suite raises the opt-in target to **21 tests**, but **21/21 was not yet reported**; do not mark as PASS.
- The new E2.2-E.2 synthetic supervisor unit suite is included in the reported **47 passed**.
- Last older completed CI confirmed success before E2.2-E.2/E.3; latest new code needs its own passing run.

## Implemented E2.2-E.2 — synthetic supervisor (not a CV sandbox)

- `backend/app/workers/synthetic_supervisor.py`: reviewed fixed Python modes only; checks lease prelaunch and during execution; attempts to terminate POSIX process group on revocation or timeout, with SIGTERM/SIGKILL and bounded grace; no parser launch.
- `backend/tests/unit/test_synthetic_supervisor.py`: 5 synthetic unit tests (success, prelaunch revocation, running revocation, timeout and unsupported mode).
- Does **not** provide a hardened execution boundary, verified descendant termination, external-effects fencing, or production orchestration.

## Implemented E2.2-E.3 — digest-only transactional publication

- `backend/app/workers/protected_output.py`: commits SHA-256 digest, byte count, worker identity/generation and job terminal status in one PostgreSQL transaction under admission advisory lock; accepts synthetic output bytes only; rejects stale/cancelled/conflicting publications.
- `backend/scripts/secops_admission_schema.sql`: disposable-only publications table, not production Alembic.
- `backend/tests/integration/test_protected_output.py`: 5 opt-in tests. **Execution and acceptance still pending.**
- `backend/scripts/secops_disposable_recovery.sh`: includes admission (6), process/recovery (5), lease (5), publication (5) suites.
- **No real output bytes or CV documents persisted.** No actual file/object destination protected by fencing.

## Immediate next validation (Codespaces)

```bash
set +e
cd /workspaces/Job-Agent-SEC-OPS-01
git fetch origin
git pull --ff-only origin feature/sec-ops-01-broker-isolation
source .venv-secops/bin/activate
cd backend
python -m ruff check .; echo "RUFF_LINT=$?"
python -m ruff format --check .; echo "RUFF_FORMAT=$?"
python -m mypy; echo "MYPY=$?"
python -m pytest tests/unit/test_job_protocol.py tests/unit/test_job_admission.py tests/unit/test_synthetic_supervisor.py -q; echo "UNIT_TESTS=$?"
cd ..
bash backend/scripts/secops_disposable_recovery.sh
```

The disposable harness must use its **own** new PostgreSQL container; never point it at preserved Codespaces DBs. Review its output for **21 passed**, no skipped tests, and cleanup. Verify the GitHub CI for the checkpoint commit. If validation fails, keep E2.2-E.2/E.3 as candidates, not accepted.

## E2.2-E.3 — disposable PostgreSQL acceptance evidence (user execution)

The user subsequently executed `bash backend/scripts/secops_disposable_recovery.sh` and provided the terminal result:

```text
21 passed, 1 warning in 9.97s
=== DISPOSABLE E2.2-D.2 ACCEPTANCE: TESTS FINISHED ===
=== STOPPING OWN DISPOSABLE DATABASE ===
```

**Acceptance:** 21/21 opt-in PostgreSQL integration tests PASS (admission 6, process recovery 5, worker lease 5, protected publication 5). The cleanup trap was invoked. The single existing Starlette/httpx deprecation warning did not fail tests. This result is **functional acceptance of the experimental metadata-only implementation**, not production security acceptance.

**Separate checks:** the previously reported unit run gave 47 PASS, Ruff lint PASS, full MyPy PASS (147 files). Ruff format had one failure, addressed in commit `9b99a18`; a post-fix Ruff format result is not included in the supplied 21-test output. The CI of the checkpoint commit was in progress at time of the latest check. Avoid claiming global CI or Ruff PASS without fresh evidence.

**Decision remains SEC/OPS Gate 1 NO-GO**, Draft PR #24. Preserve `CV_SANDBOX_REQUIRED`. Real worker sandbox, output destination fencing, identity integration and independent security acceptance remain outstanding.

## Remaining security blockers before beta with real resumes

1. Host-separated worker, least-privilege sandbox and externally reviewed isolation for untrusted files.
2. Strong workload identity and secure transport; API-session-derived user/tenant authorization.
3. Real parser-process supervision and provable termination/side-effect fencing after lease loss.
4. Actual staged output destination with atomic/fenced publish, integrity, authorization, retention/GC.
5. Operational monitoring, retries, dead-letter/poison job handling, recovery and adversarial tests.

**Decision: SEC/OPS Gate 1 NO-GO; PR #24 remains Draft.**
