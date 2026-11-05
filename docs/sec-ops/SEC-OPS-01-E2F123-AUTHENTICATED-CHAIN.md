# E2.2-F.1.2.3 — Two-hop authenticated staging chain (NOT public CV processing)

**Status:** code candidate and disposable 3-UID operational probe; **NO-GO** for customer CVs. `CV_SANDBOX_REQUIRED` unchanged; PR #24 remains Draft.

## What is now implemented

- `app/workers/secops_api_submission.py`: uses the actual backend `auth.current(session, bearer_token)` service to verify a revocable bearer token. Enforces `authorize_cv_submission()`: session subject = envelope subject, exact tenant + server-side tenant membership, explicit consent, bounded file and format. Only then signs API→gateway. **No public FastAPI route is added and there is still no tenant-membership DB implementation.** The module is not sufficient alone for real customer CVs.
- `app/workers/secops_authenticated_chain.py`: length-bounded API→gateway signed frame, strict JSON fields and duplicate-key rejection, registered `SO_PEERCRED` + API-domain HMAC + nonce admission, only then **lazy connect** to the scoped broker-owned ingress. Gateway creates a fresh nonce and broker-domain HMAC. The gateway also pins the broker's kernel `SO_PEERCRED` UID/GID **before transmitting bytes**; a spoofed listener cannot acknowledge. A successful acknowledgement must contain the SHA-256 digest of the exact request; all other replies are denied. No parser or Docker access.
- `tests/integration/test_secops_authenticated_chain.py`: in-process Unix `socketpair` regression for signed two-hop forwarding, API signature spoof, wrong OS peer registry, API replay and false broker acknowledgements.
- `tests/unit/test_secops_api_submission.py`: tests bearer-resolved subject, wrong/expired auth, tenant mismatch, missing consent and membership outage (auth is mocked in these tests).
- `scripts/secops_f123_three_service_probe.py`: disposable three-separate-process Linux lab with **real UIDs** API 61001, gateway 61002, broker 61003. API→gateway `0770` directory, gateway→broker broker-owned ingress directory `0710`/socket `0660`, broker-private SQLite nonce storage `0700`/`0600`. Probes signed delivery and OS-level access denials *while sockets are active*; uses synthetic document bytes only.

**Important limitation:** This is a *real multi-process authenticated IPC transport in a disposable container*, but **not** an integrated production FastAPI route, tenant authorization, Docker parser or enterprise deployment. Because the current schema has no tenant membership table, membership is a required injected authority and deliberately not guessed from user-controlled claims.

## Local code verification

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
```

## Cross-UID disposable operational proof

**Do not** run the root UID-switching probe on the Codespaces host. Use an owned *non-production* Docker daemon and an existing local `python:3.12-slim` image. No real CVs, host Docker socket, database mounts or secrets.

```bash
cd /workspaces/Job-Agent-SEC-OPS-01
fixture=$(mktemp -d)
chmod 755 "$fixture"
install -d -m 755 "$fixture/app" "$fixture/app/workers" "$fixture/scripts"
touch "$fixture/app/__init__.py" "$fixture/app/workers/__init__.py"
for module in job_protocol job_admission gateway_identity broker_transport_auth broker_transport_wire broker_replay_sqlite secops_authenticated_chain; do
  install -m 644 "backend/app/workers/${module}.py" "$fixture/app/workers/${module}.py"
done
install -m 644 backend/scripts/secops_f123_three_service_probe.py "$fixture/scripts/probe.py"
```

```bash
docker run --rm --pull never --network none --read-only --cap-drop ALL --cap-add CHOWN --cap-add SETUID --cap-add SETGID --security-opt no-new-privileges --pids-limit 64 --memory 256m --cpus 1 --tmpfs /tmp:rw,nosuid,nodev,size=16m --mount "type=bind,src=$fixture,dst=/opt/lab,readonly" --env PYTHONPATH=/opt/lab --env SECOPS_DISPOSABLE_ACK=I_OWN_THIS_DISPOSABLE_SANDBOX python:3.12-slim python /opt/lab/scripts/probe.py
result=$?
rm -rf "$fixture"
echo "F123_EXIT=$result"
```

Expected **eleven** true checks:
`AUTHORIZED_3_UID_HOPS`, `API_HMAC_TAMPERING_DENIED`, `API_NONCE_REPLAY_DENIED`, `API_DIRECT_BROKER_DENIED`, `UNKNOWN_GATEWAY_DENIED`, `SERVICES_EXIT_ZERO`, `GATEWAY_DIRECTORY_0770`, `BROKER_INGRESS_0710`, `BROKER_PRIVATE_0700`, `REPLAY_DB_0600`, `SEPARATE_UIDS`.

**PASS requires:** output `{"status":"PASS","checks":{...}}` with all eleven true and `F123_EXIT=0`. Exceptions and connection refusal do **not** count as permission denials. A successful CI alone is not proof of real cross-UID operation.

## Remaining before any real CV

1. Implement actual trusted tenant-membership authority in the database and attach consent evidence to the verified API identity; reject legacy local-user fallback. Add API integration tests with PostgreSQL using real bearer sessions and cross-tenant challenges.
2. Operate API and gateway as independently deployed restricted UIDs with distinct secrets; secure per-service key provisioning, rotation, rekey, time-sync and health checks. Prove Docker socket inaccessible from API/gateway in the *actual deployment*.
3. Replace the test-only `MemoryAdmissionStore` with distributed durable replay, idempotency and quota/queue implementation for API→gateway and broker admission across restarts and multiple replicas; harden response authenticity.
4. Integrate and independently audit the isolated parser container, verify actual seccomp/LSM/cgroup restrictions, no network, no host mounts or credential leakage; test malicious synthetic PDF/DOCX/TXT.
5. Add crash/cancel/retry/concurrency tests, limits, encrypted storage/retention/deletion, LGPD notice, human-review-only Master Profile/Fact Ledger confirmation, monitoring and operational rollback.
6. An explicit final SEC/OPS Gate 1 beta signoff is needed before removing `CV_SANDBOX_REQUIRED`.

Until then: **PR Draft; SEC/OPS Gate 1 NO-GO; no real-person CV uploads**.

## CI evidence — contract tests PASS, operational probe still pending

At code commit `d930c228b18b93f2b80045e4694b1d2a9bbc40c5`, [GitHub Actions run #41950801794](https://github.com/Arthur-Levi/Job-Agent/actions/runs/41950801794), backend job **SUCCESS**:
- `ruff check .` PASS, `ruff format --check .` PASS (**173 formatted files**).
- `mypy` PASS (**164 source files**).
- `pytest` **455 passed, 21 skipped, 3 xfailed, 1 warning**. This includes 7 two-hop `socketpair` tests and 7 API bearer/consent/tenant adapter tests, **all synthetic**.
- Audit, frontend, browser-smoke and sandbox-smoke SUCCESS; the real-browser-postgres-e2e job was still executing at the evidence capture.

**Not accepted yet:** F.1.2.3 cross-UID live-socket lab (11 tests in disposable Docker). Only the operator's JSON + `F123_EXIT=0` can certify that operational scope. Neither CI nor this probe certifies a real production API route or tenant database membership.

## Operator acceptance evidence — **F.1.2.3 11/11 PASS** (2026-11-04 / 2026-11-05)

Operator-provided terminal log from the Codespaces security worktree, branch `feature/sec-ops-01-broker-isolation` at `HEAD=5323640` synchronized with `origin` and clean `git status --short --branch`:

```text
14 passed, 1 warning in 0.14s
All checks passed!
173 files already formatted
Success: no issues found in 164 source files
```

The operator then prepared the self-contained fixture in a temporary directory and executed the bounded disposable `python:3.12-slim` container with `--rm --pull never --network none --read-only --cap-drop ALL --cap-add CHOWN --cap-add SETUID --cap-add SETGID --security-opt no-new-privileges --pids-limit 64 --memory 256m --cpus 1`, `--tmpfs /tmp:rw,nosuid,nodev,size=16m`, **read-only fixture mount**, `PYTHONPATH=/opt/lab` and explicit disposable lab acknowledgement. The container was not granted the host Docker socket, app credentials, real CVs or application database. The operator removed the fixture after execution.

Observed complete result:

```json
{"checks":{"API_DIRECT_BROKER_DENIED":true,"API_HMAC_TAMPERING_DENIED":true,"API_NONCE_REPLAY_DENIED":true,"AUTHORIZED_3_UID_HOPS":true,"BROKER_INGRESS_0710":true,"BROKER_PRIVATE_0700":true,"GATEWAY_DIRECTORY_0770":true,"REPLAY_DB_0600":true,"SEPARATE_UIDS":true,"SERVICES_EXIT_ZERO":true,"UNKNOWN_GATEWAY_DENIED":true},"status":"PASS"}
```

```text
F123_EXIT=0
```

**Accepted: F.1.2.3 3-process / 3-UID synthetic operational lab, 11/11 PASS.** This proves a correctly signed synthetic request traversed the laboratory API→gateway→broker chain, HMAC tampering and API nonce replay were denied, direct API→broker and unauthorized→gateway access was denied by filesystem credentials, directory/private database modes were enforced, and the services exited without errors. This is **not** a live production FastAPI endpoint and does not prove real tenant membership, customer document handling, parser execution, production Docker authority isolation or distributed replay/quota behavior.

At the source checkpoint `5323640`, [GitHub Actions #41951282929](https://github.com/Arthur-Levi/Job-Agent/actions/runs/41951282929) completed **all six jobs successfully**: backend, frontend, audit, sandbox-smoke, browser-smoke and real-browser-postgres-e2e. Backend summary: **455 passed, 21 skipped, 3 xfailed, 1 warning**; Ruff PASS (173 files); MyPy PASS (164 source files).

**Release decision stays unchanged:** `CV_SANDBOX_REQUIRED` active, PR #24 Draft, SEC/OPS Gate 1 **NO-GO** for real customer CVs. Advance to parser sandbox operational acceptance and actual tenant/consent authority only under explicit subsequent gated changes.
