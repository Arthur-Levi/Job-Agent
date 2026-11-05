# JOB AGENT — SEC/OPS CHECKPOINT F.1.2.3 (2026-11-05)

**Project:** Arthur-Levi/Job-Agent  
**Working branch:** `feature/sec-ops-01-broker-isolation`  
**Checkpoint source HEAD validated by operator:** `53236402bb94e1f65e01198dd18185bc79c10813` (`5323640`)  
**Pull Request:** [#24](https://github.com/Arthur-Levi/Job-Agent/pull/24) — **DRAFT**  
**Security issue:** [#23](https://github.com/Arthur-Levi/Job-Agent/issues/23)  
**Overall SEC/OPS Gate 1:** **NO-GO**; external/customer CVs NOT authorized.  
**Production upload kill switch:** `503 CV_SANDBOX_REQUIRED` preserved.

> Scope statement: This checkpoint is a documentation and reproducibility snapshot.
> PASS refers strictly to tested synthetic contracts and disposable Linux
> laboratory operational evidence. It does not certify a deployed production
> parser or legal readiness for processing real-user CVs.

## 1. Completed checkpoints

| Stage | Implemented/tested scope | Evidence | Decision |
|---|---|---|---|
| D1 / D2 historical | API, React, profile/Fact Ledger, DB migrations, initial import pipeline | Earlier checkpoint documents and CI | Historical baseline; no live CV clearance |
| SEC/OPS F.1.1 | Disposable cross-UID service/socket isolation | `backend/scripts/secops_f111_identity_probe.py`; operator 8/8 checks true, `F111_EXIT=0` | **PASS lab** |
| F.1.2 | Synthetic signed gateway→broker contract, bounded frames, tamper and replay rejection | 14 local PASS, prior backend 416 PASS | **PASS synthetic** |
| F.1.2.1 | Broker-owned ingress, Linux peer UID/GID, broker-private SQLite nonce ledger; restart replay | `docs/sec-ops/SEC-OPS-01-E2F121-CROSS-UID-DURABLE-REPLAY.md`; operator 10/10 true, `F121_EXIT=0`; SQLite 9 local PASS on Python 3.14 | **PASS lab** |
| F.1.2.2 | Fail-closed CV admission policy: consent, identity/tenant matching with injected authority, format signatures, file length, redacted errors | `docs/sec-ops/SEC-OPS-01-E2F122-REAL-CV-READINESS.md`; operator 16 local PASS; CI backend 441 PASS | **PASS policy tests only** |
| **F.1.2.3** | Real 3-process/3-Linux-UID **synthetic** API→gateway→broker transport, separate signatures, reciprocal SO_PEERCRED, nonce replay denial, filesystem denials | `docs/sec-ops/SEC-OPS-01-E2F123-AUTHENTICATED-CHAIN.md`; operator **11/11 true**, `F123_EXIT=0`; 14 local PASS; latest code CI backend **455 PASS** | **PASS lab** |

**Important:** “real” in F.1.2.3 means **real Linux processes and IPC permissions**, not actual public API traffic or real candidate files.

## 2. F.1.2.3 reproducible acceptance record

**Operator's working tree prior to evidence:** `/workspaces/Job-Agent-SEC-OPS-01/backend`, branch `feature/sec-ops-01-broker-isolation`, HEAD `5323640`, tracking `origin/feature/sec-ops-01-broker-isolation`, no local changes listed.

Local test output:

```text
14 passed, 1 warning in 0.14s
All checks passed!
173 files already formatted
Success: no issues found in 164 source files
```

The single warning is a known Starlette/httpx test client deprecation warning; it is **not** a CV sandbox security certification.

Operator's disposable Linux test output:

```json
{
  "checks": {
    "API_DIRECT_BROKER_DENIED": true,
    "API_HMAC_TAMPERING_DENIED": true,
    "API_NONCE_REPLAY_DENIED": true,
    "AUTHORIZED_3_UID_HOPS": true,
    "BROKER_INGRESS_0710": true,
    "BROKER_PRIVATE_0700": true,
    "GATEWAY_DIRECTORY_0770": true,
    "REPLAY_DB_0600": true,
    "SEPARATE_UIDS": true,
    "SERVICES_EXIT_ZERO": true,
    "UNKNOWN_GATEWAY_DENIED": true
  },
  "status": "PASS"
}
```

```text
F123_EXIT=0
```

**Scope and execution:** disposable `python:3.12-slim` with `--network none`, `--read-only`, `--cap-drop ALL` except `CHOWN,SETUID,SETGID`, `--security-opt no-new-privileges`, 64 PIDs, 256 MB RAM, one CPU, private 16 MB tmpfs, explicit code-only read-only fixture mount; **no host docker.sock, production credentials, application database, or customer CVs**. Fixture deleted after completion.

**GitHub Actions evidence (source commit `5323640`):**
- [Run #41951282929](https://github.com/Arthur-Levi/Job-Agent/actions/runs/41951282929): **all six jobs SUCCESS** — backend, frontend, audit, sandbox-smoke, browser-smoke and real-browser-postgres-e2e.
- Backend: **455 passed, 21 skipped, 3 xfailed, 1 warning**; Ruff lint PASS; format PASS (**173 files**); MyPy PASS (**164 source files**).
- Do not interpret the browser/PostgreSQL suite as an authorization of the real CV ingestion path.

## 3. Architecture and source of truth

**Public API:** `backend/app/main.py`; `backend/app/api/v1/router.py`; `backend/app/api/v1/auth.py`; `backend/app/api/v1/resume_imports.py`; `backend/app/api/deps.py` (revocable bearer sessions, preview route **still 503 in production**).

**Admission and identity:**
- `backend/app/workers/job_protocol.py` — strict bounded job envelope (submit/status/cancel), max document 2 MB.
- `backend/app/workers/job_admission.py` — API→gateway HMAC, strict nonce, in-memory synthetic admission; **not distributed/durable for the first hop**.
- `backend/app/workers/gateway_identity.py` — registered service ID and Linux `SO_PEERCRED` UID/GID.
- `backend/app/workers/cv_real_intake.py` — consent, tenant and trusted subject policy, basic signatures and no PII in error representations, **unwired**.
- `backend/app/workers/secops_api_submission.py` — derives subject from existing `auth.current()` bearer/session service, checks membership through an injected interface, creates signed first-hop message. **Not a public route, and no operational membership authority exists yet.**

**IPC / broker:**
- `backend/app/workers/broker_transport_auth.py` — separate gateway→broker HMAC domain and registered gateway SO_PEERCRED admission.
- `backend/app/workers/broker_transport_wire.py` — framed transport, bounded frame and strict field validation.
- `backend/app/workers/broker_replay_sqlite.py` — broker-owned private SQLite replay store, atomic nonce insertion, mode 0600 and 0700 directory checks; **single-host lab only**.
- `backend/app/workers/secops_authenticated_chain.py` — real 2-hop signed relay; rejects API messages before connecting to broker, checks broker SO_PEERCRED before transmitting data, matches broker ACK to SHA-256 digest. **Not deployed as actual API/gateway services**.
- `backend/scripts/secops_f121_cross_uid_probe.py`; `backend/scripts/secops_f123_three_service_probe.py` — isolated disposable operator probes.
- `backend/app/workers/resume_broker.py` — older private parser broker, **not yet connected** to F.1.2.3 transport.

**Parser and career data:**
- `backend/app/services/resume_worker.py`; `backend/app/workers/resume_parser.py`; `backend/app/services/resume_preview.py` — bounded PDF/DOCX/TXT processing and reviewable ATS-style preview. Existing parser subprocess mode is **not** an accepted OS sandbox.
- Master Profile, Fact Ledger, explicit confirmation and review contracts exist, but their end-to-end gated real-CV integration remains pending.

## 4. Security boundaries NOT to relax

- Retain `CV_SANDBOX_REQUIRED` fail-closed and `PR #24` Draft.
- API UID must not gain `docker.sock`, Docker authority, broker UID or access to the private broker socket.
- Gateway UID must not gain the private broker socket; it may only reach a separate broker-owned ingress via a specifically scoped Unix group.
- Hardened parser must be non-root, no network, read-only filesystem, drop capabilities, no new privileges, enforce seccomp and AppArmor/SELinux plus bounded CPU/RAM/PIDs/timeouts, no secrets or host mounts.
- Keep raw CVs, filenames and user data out of security logs; prefer minimal opaque audit identifiers.
- No external real-person CVs or beta document ingestion until explicit end-to-end independent gate acceptance.

## 5. Open blockers (prioritized)

### P0 — required before first real-user CV

1. **Tenant model and consent evidence:** trustworthy DB-backed tenant membership, session-based subject binding and consent proof; tests with revoked sessions, cross-tenant attempts, authorization service outage and replay.
2. **Real service deployment:** actual API→gateway→broker with distinct identities, separate secrets and real process lifecycle; no unauthenticated fallback, no bypass to `resume_broker.py`.
3. **Distributed admission:** durable replay on both hops, idempotency, tenant/user/global quotas, cancellation, duplicate detection, atomic queue transitions, restart/retry recovery and multi-instance semantics.
4. **Parser isolation + adversarial synthetic documents:** connect only behind authenticated broker, prove runtime restrictions on deployed host, verify malformed PDF, DOCX ZIP expansion, invalid TXT, resource exhaustion, failed cleanup, timeout and cancellation.
5. **Privacy, retention and human approval:** LGPD purpose/consent, sensitive log redaction, retention/deletion process, backups, documented incident response; user reviews extracted records before Master Profile and Fact Ledger commits.
6. **Gate 1 independent decision:** signed test evidence and reviewed rollback/runbooks, only then consider switching `503 CV_SANDBOX_REQUIRED` for tightly limited beta.

### P1 — quality and reliability after P0

- External durable backup/restore rehearsal; key lifecycle and secret rotation; monitoring/alerting; staging stress tests and load shedding; forward-compatible protocol migration; observability without PII.
- Test warning modernization (Starlette/httpx) when safe and separately validated.

## 6. Safe next mission and runbook

**Next milestone:** E2.2-F.1.2.4 — integrate the isolated parser with hardened broker-owned execution, exclusively using self-authored synthetic PDF/DOCX/TXT test documents, verify kernel/cgroup/LSM restrictions, and keep all public CV traffic blocked.

```bash
cd /workspaces/Job-Agent-SEC-OPS-01
git status --short --branch
git fetch origin
git pull --ff-only origin feature/sec-ops-01-broker-isolation
source .venv-secops/bin/activate
cd backend
python -m pytest tests/integration/test_secops_authenticated_chain.py tests/unit/test_secops_api_submission.py -v
python -m ruff check .
python -m ruff format --check .
python -m mypy
git log -1 --oneline
```

**Post-checkpoint policy:** preserve a dedicated checkpoint branch `checkpoint/secops-f123-2026-11-05` at the documentation commit; continue implementation on `feature/sec-ops-01-broker-isolation`. Do **not** merge the Draft PR into the default branch or claim a live beta release.

## 7. Linked evidence

- [F.1.1 Operational Identities](SEC-OPS-01-E2F11-OPERATIONAL-IDENTITIES.md)
- [F.1.2 Synthetic Authenticated Transport](SEC-OPS-01-E2F12-AUTHENTICATED-TRANSPORT.md)
- [F.1.2.1 Cross-UID + Replay](SEC-OPS-01-E2F121-CROSS-UID-DURABLE-REPLAY.md)
- [F.1.2.2 CV Intake](SEC-OPS-01-E2F122-REAL-CV-READINESS.md)
- [F.1.2.3 Authenticated Chain](SEC-OPS-01-E2F123-AUTHENTICATED-CHAIN.md)
- [Security issue #23](https://github.com/Arthur-Levi/Job-Agent/issues/23)
- [Security PR #24](https://github.com/Arthur-Levi/Job-Agent/pull/24)
