# E2.2-F.1.2.2 — Real CV readiness: strictly staged, no public enablement

**Status: P0 implementation candidate, NO-GO for live customer CVs.** PR #24 Draft. Keep `503 CV_SANDBOX_REQUIRED`. Previous F.1.2.1 PASS (10/10) proved **synthetic IPC**, not approval for arbitrary user files.

## Already exists in this repository

- `app/services/resume_preview.py` supports local text extraction of PDF, DOCX and TXT, with explicit 2 MB file size, PDF page, DOCX zip expansion, text and section-review limits. Its heuristic output is a **reviewable preview**, not confirmed profile facts or actual third-party ATS certification.
- `app/workers/resume_parser.py` is a parser entrypoint with process resource limits.
- `app/services/resume_worker.py` contains restricted Docker launch parameters, but can also use `subprocess` (not a hardened sandbox), `container` and an older private broker protocol. This is **not evidence** of secure production deployment. In particular, the gateway signed transport implemented in F.1.2 is not wired to the old resume broker.
- `app/workers/broker_transport_auth.py`, `broker_transport_wire.py` and `broker_replay_sqlite.py` are tested separately. F.1.2.1 successfully proved synthetic broker-owned ingress across distinct Linux UIDs with durable replay in a disposable container.

## New P0 admission layer (this commit)

`app/workers/cv_real_intake.py` is a **pure**, deliberately unwired future live-CV admission contract:
1. A **trusted server-side authenticated user ID** must equal the envelope's subject user ID.
2. The requested tenant must equal the envelope's tenant and a separate **server-side membership authorizer** must approve submission. Reject caller-supplied tenant claims as authority; do not substitute a simple trusted-looking boolean at the public boundary.
3. Require explicit processing consent recorded by the caller's consent workflow.
4. Enforce file bytes limit and verify basic format signatures for `pdf` (`%PDF-`), `docx` (`PK\\x03\\x04`), `txt` (strict UTF-8 and no NUL). **This header check does not establish file safety**; the full file must be parsed **only inside the sandbox**. Reject other content types and malformed headers.
5. Keep document data in an ephemeral no-repr submission object and produce only its SHA-256 digest for audit correlation. Do not log contents, filenames or full object representations.
6. The module neither reads files nor opens sockets nor runs a parser. It **cannot** by itself authorize a public CV release.

Unit tests use fake documents only, covering PDF/DOCX/TXT headers, spoofed extensions, invalid bytes, absence of consent, mismatched user/tenant, lack of membership and redaction.

## Non-negotiable gates BEFORE the first real CV (all P0)

| Gate | Required proof | Status |
|---|---|---|
| Authenticated subject and tenant | Authenticated API session, verified tenant membership, negative cross-tenant tests and server-side consent receipts | **PENDING end-to-end wiring** |
| Authenticated IPC | Real API UID → gateway UID → broker-owned ingress UID, independent processes and signatures; no user-claimed UID/tenant | **PENDING real wiring** |
| Docker/runtime authority | API and gateway provably cannot call Docker or read docker.sock; broker has a restricted, audited runtime authority | **PENDING operational proof** |
| Parser container sandbox | Network none, rootfs read-only, seccomp + AppArmor/SELinux, no secrets/host mounts/privileged capabilities, cgroup CPU/RAM/PIDs/timeouts and worker cleanup | **PENDING operational proof** |
| Durable admission controls | Durable replay, idempotency, per-user/per-tenant quota, queue/cancel/retry, crash recovery and multi-instance concurrency | **PENDING production acceptance** |
| Privacy & retention (LGPD) | Consent/notice, encrypted storage where required, minimal retention, access/deletion requests, redacted logs, audit and backups | **PENDING product/legal signoff** |
| Parser robustness | Adversarial PDF, DOCX ZIP bombs, malicious content, crashes, timeouts, path traversal and oversized output under isolated fixture tests | **PENDING abuse acceptance** |
| Human review | No automatic creation of confirmed facts; user reviews extraction before Master Profile/Fact Ledger transaction | **PENDING integrated acceptance** |

**Kill switch:** `CV_SANDBOX_REQUIRED` must remain in force in the API path; do not add an environment-only bypass, loosen 0700/0600 permissions of the private parser socket, grant API docker.sock access, or claim the F.1.2.1 lab already covers real CV processing.

## Roadmap

- **F.1.2.2**: P0 intake policy and adversarial unit tests (this increment; not live). 
- **F.1.2.3**: Wire verified API session/tenant consent to broker-owned ingress **using separate process identities**; broker validates signed workload and its own authorization before submitting bounded documents; documented negative cases.
- **F.1.2.4**: Connect broker to hardened ephemeral CV parser under dedicated non-root identity, test with **self-authored synthetic PDFs/DOCX/TXT only**, record runtime invariants including no network/Docker socket from API/gateway.
- **F.1.2.5**: Add transactional persistence and controlled user approval, durable quotas/cancel/recovery, retention policy, privacy review and operational incident procedures.
- **Gate 1 review**: independent security signoff and abuse tests, then limited and consented beta on a staging-grade deployment. Until signoff, do not send customer CVs.

## Local validation

```bash
cd /workspaces/Job-Agent-SEC-OPS-01
git fetch origin
git pull --ff-only origin feature/sec-ops-01-broker-isolation
source .venv-secops/bin/activate
cd backend
python -m pytest tests/unit/test_cv_real_intake.py -v
python -m ruff check .
python -m ruff format --check .
python -m mypy
```

## CI validation of the P0 intake layer

[GitHub Actions run #41948022622](https://github.com/Arthur-Levi/Job-Agent/actions/runs/41948022622), code commit `edd5537`, backend **SUCCESS**:
- Ruff lint PASS, Ruff format PASS (168 files), MyPy PASS (160 source files).
- Pytest **441 passed, 21 skipped, 3 xfailed, 1 warning**, including **16 new** `test_cv_real_intake.py` cases.
- This is **synthetic input admission only**, not parser invocation, live CV support, or an end-to-end authorization test. All F.1.2.2 proof remains scoped to the pure policy and its mocks.


## Operator Codespaces local acceptance — 16/16 PASS

Operator-provided terminal output from `/workspaces/Job-Agent-SEC-OPS-01/backend`, security branch `feature/sec-ops-01-broker-isolation`, `HEAD=9895098` aligned with origin:

```text
16 passed, 1 warning in 0.05s
All checks passed!                     # Ruff lint
168 files already formatted           # Ruff format
Success: no issues found in 160 source files  # MyPy
```

**Decision: F.1.2.2 pure-policy unit suite + local quality gate PASS.** Prior [GitHub Actions run #41948022622](https://github.com/Arthur-Levi/Job-Agent/actions/runs/41948022622) also had all six jobs green, backend 441 tests passed. This does not represent a real-user CV, integration of verified API session or tenant store, real authenticated API→gateway→broker, hardened parser, or LGPD approval. Keep SEC/OPS Gate 1 NO-GO and `CV_SANDBOX_REQUIRED` in effect.
