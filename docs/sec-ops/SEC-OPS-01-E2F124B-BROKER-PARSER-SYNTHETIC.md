# SEC/OPS — E2.2-F.1.2.4-B: synthetic-only broker → parser prototype

**Security status:** UNIT/INTEGRATION PROTOTYPE, **not** a production-enabled parser service; **SEC/OPS Gate 1 NO-GO** and `CV_SANDBOX_REQUIRED` remain. F.1.2.3 preserved at `checkpoint/secops-f123-2026-11-05`. The F.1.2.4 Docker/LSM operational proof is still NO-GO in Codespaces.

## Implemented (not wired to the API)

- `backend/app/workers/secops_f124b_broker_parser.py`: one-call in-process prototype for a broker-side **already accepted UNIX connection**.
- Reads a bounded signed frame and calls `BrokerTransportGate.admit()` with trusted socket `SO_PEERCRED`, registered gateway HMAC, timestamp and replay store before any parser execution. Then validates the strict job envelope.
- Permits **only `submit` for fixed synthetic user `11111111-1111-4111-8111-111111111111`, tenant `synthetic-f124`, with byte-for-byte matches to the three valid self-generated fixtures**. Denies any other user, tenant, file, malformed signed frame, signature, nonce replay or unknown operation *before* attestation/executor.
- Verifies **runtime isolation BEFORE spawning a parser**; default verifier performs the 12/12 F.1.2.4 opt-in Docker laboratory and will fail on the previously observed `unconfined` Codespaces host. Test doubles are injectable **only in the prototype test seam**; do not use them in deployment.
- Bounded semaphore of two concurrent requests; strict wall clock and bounded response reuse existing `_run_bounded` / `_container_command`. All isolated parser containers are force-cleaned on error, timeout and normal completion.
- Releases semaphore on failure. Converts all executor failure details into opaque errors. Returns only request SHA-256, document format, section labels and item count — no extracted CV text, filename or identity.
- No socket listener, no new API route, no running worker daemon, no import into `resume_imports` or `resume_broker`; this is **not** a production pipeline, real user tenant authorization, persistent job queue, durable distributed cancellation, quotas or idempotency.

## Test scope

`backend/tests/integration/test_secops_f124b_broker_parser.py`: synthetic UNIX socketpair using actual kernel peer credentials, signed gateway transport and in-memory replay stub. Tests valid authorized synthetic job, bad HMAC, non-whitelisted bytes, other tenant, other user, denied runtime attestation, nonce replay, saturated semaphore, executor failure redaction/semaphore cleanup, missing operator opt-in and malformed parser output.

Unit tests do **not** prove an actual three-process IPC deployment, durable replay or LSM confinement. The production parser remains gated.

## Reproducible validation (Codespaces; no Docker execution)

```bash
cd /workspaces/Job-Agent-SEC-OPS-01
git status --short --branch
git fetch origin
git pull --ff-only origin feature/sec-ops-01-broker-isolation
source backend/.venv-f124/bin/activate
cd backend
python -m pytest tests/integration/test_secops_f124b_broker_parser.py -v
python -m pytest tests/unit/test_secops_synthetic_parser_lab.py -v
python -m ruff check .
python -m ruff format --check .
python -m mypy
git status --short --branch
```

**Operator rule:** do not set `SECOPS_F124_ACK` on a host whose parser reports `unconfined`; the isolated Docker test remains NO-GO until a separate LSM-enforcing VM is provisioned. The existing F.1.2.4 VM runbook is `docs/sec-ops/SEC-OPS-01-E2F124-VM-OPERATIONAL-ACCEPTANCE.md`.

## Remaining mandatory work

1. Secure VM runtime 12/12 PASS with enforced AppArmor/SELinux and evidence of actual cgroup limits, rootfs read-only, filesystem/mount isolation.
2. Broker **actual separate process and private filesystem socket**, authenticated only from gateway UID, with the isolated parser dispatch under broker authority, not the legacy unauthenticated `resume_broker.py`.
3. Trusted real server-side tenant membership, explicit consent, request-level idempotency and durable distributed quotas/replay/queue, cancellation, crash recovery, retention, privacy, LGPD.
4. Additional adversarial PDF/DOCX/TXT tests and signed artifact/image pinning.
5. Independent Beta Acceptance SEC/OPS Gate 1 review and signoff.

**No-Go preserved:** do not permit real candidate documents, remove `503 CV_SANDBOX_REQUIRED`, merge the Draft PR or claim production readiness.


## Automated evidence — 2026-11-05

Code commit `a8ffed8c0753767c3bd7205187b94c340790fdbe`, [GitHub Actions run #42120555171](https://github.com/Arthur-Levi/Job-Agent/actions/runs/42120555171):

- Backend job **SUCCESS**: Ruff lint PASS; Ruff format **178 files**; MyPy **168 files**; Pytest **481 passed, 21 skipped, 3 xfailed, 1 warning**. New F.1.2.4-B integration suite: **11 passing**.
- Audit, sandbox-smoke, frontend and browser-smoke jobs succeeded; real-browser-postgres-e2e pending when this note was recorded. The backend and synthetic parser tests do **not** constitute operational LSM sandbox approval.
- No new production API route or real CV data processing. Codespaces isolation is still `unconfined`, so operational F.1.2.4 remains **NO-GO**.
