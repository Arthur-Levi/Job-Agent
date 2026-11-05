# E2.2-F.1.2.1 — Disposable cross-UID broker-owned ingress and durable replay

**Decision before operator execution:** implementation candidate; operational evidence pending. SEC/OPS Gate 1 **NO-GO**, PR #24 Draft, keep `503 CV_SANDBOX_REQUIRED`.

## Isolated lab architecture

- API: UID 61001, primary GID 61010; **not** in broker transport group.
- Gateway: UID 61002, primary GID 61010 and supplementary GID 61020.
- Broker ingress: UID 61003, GID 61020; broker-owned ingress directory `0710`, Unix socket `0660`.
- Broker-private state: UID 61003, private directory `0700`, durable SQLite nonce ledger `0600`.
- Unknown client: UID/GID 61004; no gateway or broker privileges.
- The ingress socket is **not the original resume_broker.py private parser socket**. The actual parser broker is never started. An additional group for *only the gateway* permits reaching the new broker-owned ingress without sharing broker UID, exposing docker.sock, or granting the API that group.
- The broker verifies kernel `SO_PEERCRED` UID/GID **AND** gateway-specific HMAC, bounded timestamp and unique nonce. The SQLite ledger inserts nonces atomically and survives broker process restart.
- The only permitted message is a generated **synthetic status** envelope with random UUIDs. No PDF, TXT, DOCX, Docker, real API, external networks or Job Agent database.
- This proves one possible IPC topology, **not** an end-to-end production gateway→real parser broker integration.

## Artifacts
- `backend/app/workers/broker_replay_sqlite.py`: durable broker-owned SQLite replay store; atomic `BEGIN IMMEDIATE` and unique (service, nonce); fail-closed on unavailable/corrupted database, validates private file/directory.
- `backend/tests/unit/test_broker_replay_sqlite.py`: restart persistence, single winner under concurrent connections, expiry, rejecting nonprivate dir and symlink, malformed/unavailable DB.
- `backend/scripts/secops_f121_cross_uid_probe.py`: opt-in multi-UID synthetic ingress harness. Subprocess roles and kernel peer identity are real; **no** `CAP_KILL`, `CAP_FOWNER`, `CAP_DAC_OVERRIDE` or host socket mounts.

## Operator runbook — use disposable Docker daemon only

Never execute the UID-switching probe directly as root in a persistent Codespaces host. Docker command requires an owned disposable Linux development daemon; confirm it is not production and does not expose secrets or databases. The container itself receives no Docker socket.

From the security worktree, prepare a code-only fixture. Only the explicitly listed non-secret Python modules are copied:

```bash
cd /workspaces/Job-Agent-SEC-OPS-01
git status --short --branch
git fetch origin
git pull --ff-only origin feature/sec-ops-01-broker-isolation
source .venv-secops/bin/activate
cd backend
python -m pytest tests/unit/test_broker_replay_sqlite.py -v
python -m ruff check app/workers/broker_replay_sqlite.py scripts/secops_f121_cross_uid_probe.py tests/unit/test_broker_replay_sqlite.py
python -m ruff format --check app/workers/broker_replay_sqlite.py scripts/secops_f121_cross_uid_probe.py tests/unit/test_broker_replay_sqlite.py
```

```bash
cd /workspaces/Job-Agent-SEC-OPS-01
fixture=$(mktemp -d)
chmod 755 "$fixture"
install -d -m 755 "$fixture/app" "$fixture/app/workers" "$fixture/scripts"
touch "$fixture/app/__init__.py" "$fixture/app/workers/__init__.py"
for module in job_protocol job_admission gateway_identity broker_transport_auth broker_transport_wire broker_replay_sqlite; do
  install -m 644 "backend/app/workers/${module}.py" "$fixture/app/workers/${module}.py"
done
install -m 644 backend/scripts/secops_f121_cross_uid_probe.py "$fixture/scripts/probe.py"
```

Run the **single-line** command (avoids shell line-continuation copy mistakes):

```bash
docker run --rm --pull never --network none --read-only --cap-drop ALL --cap-add CHOWN --cap-add SETUID --cap-add SETGID --security-opt no-new-privileges --pids-limit 64 --memory 256m --cpus 1 --tmpfs /tmp:rw,nosuid,nodev,size=16m --mount "type=bind,src=$fixture,dst=/opt/lab,readonly" --env PYTHONPATH=/opt/lab --env SECOPS_DISPOSABLE_ACK=I_OWN_THIS_DISPOSABLE_SANDBOX python:3.12-slim python /opt/lab/scripts/probe.py
result=$?
rm -rf "$fixture"
echo "F121_EXIT=$result"
```

Expected **ten** checks true: `AUTHORIZED`, `REPLAY` (same signed nonce after broker restart), `TAMPERED`, `FORGED_SERVICE`, `API_BLOCKED`, `UNKNOWN_BLOCKED`, `INGRESS_DIRECTORY_0710`, `BROKER_DIRECTORY_0700`, `REPLAY_DB_0600`, `DISTINCT_UIDS`. Only accept `{"status":"PASS",...}` with every check true **and** `F121_EXIT=0`. Record all denial causes; socket-not-found never qualifies as permission denial.

## Boundaries and pending
1. This lab uses a hard-coded **nonproduction fixture key**, intentionally never used for real jobs. Production gateway/broker keys must be distinct from API keys, provisioned through secrets management, rotated, and removed from logs.
2. SQLite ledger is broker-owned and survives the simulated broker restart **inside one disposable container**, but it has **not** been validated for multi-host failover, key rotation, or a production replay/storage lifecycle.
3. The lab broker returns only `ACCEPTED` / opaque denial code; it never calls resume parsing or the real `ResumeBroker`.
4. Production must verify per-tenant permissions, rebind authenticated subject, enforce durable quotas, recover from crashes, and ensure the API cannot read the ingress socket or obtain Docker authority.
5. Keep `CV_SANDBOX_REQUIRED` until all deployment isolation, abuse tests, operational runbooks and beta safety gates independently pass.

**Do not mark runtime F.1.2.1 PASS based on GitHub CI alone.** Operator container JSON + exit code are required.
