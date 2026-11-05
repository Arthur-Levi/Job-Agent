# E2.2-F.1.2.3 — Two-hop authenticated staging chain (NOT public CV processing)

**Status:** code candidate and disposable 3-UID operational probe; **NO-GO** for customer CVs. `CV_SANDBOX_REQUIRED` unchanged; PR #24 remains Draft.

## What is now implemented

- `app/workers/secops_api_submission.py`: uses the actual backend `auth.current(session, bearer_token)` service to verify a revocable bearer token. Enforces `authorize_cv_submission()`: session subject = envelope subject, exact tenant + server-side tenant membership, explicit consent, bounded file and format. Only then signs API→gateway. **No public FastAPI route is added and there is still no tenant-membership DB implementation.** The module is not sufficient alone for real customer CVs.
- `app/workers/secops_authenticated_chain.py`: length-bounded API→gateway signed frame, strict JSON fields and duplicate-key rejection, registered `SO_PEERCRED` + API-domain HMAC + nonce admission, only then **lazy connect** to the scoped broker-owned ingress. Gateway creates a fresh nonce and broker-domain HMAC. A successful acknowledgement must contain the SHA-256 digest of the exact request; all other replies are denied. No parser or Docker access.
- `tests/integration/test_secops_authenticated_chain.py`: in-process Unix `socketpair` regression for signed two-hop forwarding, API signature spoof, wrong OS peer registry, API replay and false broker acknowledgements.
- `tests/unit/test_secops_api_submission.py`: tests bearer-resolved subject, wrong/expired auth, tenant mismatch, missing consent and membership outage (auth is mocked in these tests).
- `scripts/secops_f123_three_service_probe.py`: disposable three-separate-process Linux lab with **real UIDs** API 61001, gateway 61002, broker 61003. API→gateway `0770` directory, gateway→broker broker-owned ingress directory `0710`/socket `0660`, broker-private SQLite nonce storage `0700`/`0600`. Probes signed delivery and OS-level access denials; uses synthetic document bytes only.

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
