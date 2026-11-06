# SEC/OPS — E2.2-F.1: API / gateway / broker identity boundary

**Checkpoint state: implementation candidate, runtime identities NOT proven; SEC/OPS Gate 1 NO-GO.** Branch `feature/sec-ops-01-broker-isolation`, PR #24 Draft, Issue #23. Keep `503 CV_SANDBOX_REQUIRED`.

## What we are solving

A direct API connection to the existing private broker socket is not viable under distinct UIDs: the broker requires a `0700` parent directory and a `0600` socket. Giving the API the broker UID, sharing docker.sock or relaxing the broker socket to world-access would defeat the privilege boundary.

## Proposed topology (not deployed)

```text
Internet -> API (uid: api, no Docker)
                  |
                  | Authenticated request derived from API user session
                  | Local front-door Unix socket, restricted to a dedicated group
                  v
             IPC gateway (uid: gateway, no Docker)
                  | verify Linux SO_PEERCRED, HMAC, nonce/replay,
                  | scoped tenant/subject and quotas
                  |
                  | separate constrained authenticated broker transport
                  v
             Broker (uid: broker, owns private 0700/0600 socket,
                     only service with container-runtime authority)
                  |
                  v
             Parser sandbox (nonroot, no network/secrets)
```

**Access bridge remains a deployment design requirement.** The gateway cannot directly access the broker's private socket as a different Unix identity; broker-facing transport must use an independent authenticated service-to-service mechanism (mTLS on a private namespace, a pre-authorized broker-side acceptor, or equivalent). *Do not silently change directory permissions or merge identities.*

## Implemented candidate — code only

`backend/app/workers/gateway_identity.py` defines:
- `AuthorizedWorkload(service_id, uid, gid)` (explicit registry);
- `GatewayIdentityGate.peer_identity(sock)` uses Linux kernel `SO_PEERCRED`, not JSON-supplied identities;
- `GatewayIdentityGate.admit(...)` first checks registered OS UID/GID and then delegates signature/timestamp/nonce/payload validation and admission to `AdmissionService`.
- fail-closed on unsupported OS, unknown identities, wrong UID/GID, bad signature, expired timestamp or replay (subject to configured durable admission store).

`backend/tests/unit/test_gateway_identity.py` exercises Linux Unix socketpair peer credentials, known/unknown services, invalid HMAC, forbidden broker/API same UID and simulated UID mismatch. **Socketpair between two sockets of the same process does not prove isolation across real UID namespaces.**

**Not wired to existing `resume_broker`, upload API, Docker or production databases.** Existing `AdmissionService` with `MemoryAdmissionStore` is unit-test only and cannot provide distributed replay protection in production. A separate gateway listener, secure API-to-gateway socket policy, gateway-to-broker authenticated transport and real workload identity attestation remain to be implemented.

## Identity and access matrix — required future acceptance

| Principal | API session/DB | Gateway socket | Private broker socket | Docker/container authority |
|---|---|---|---|---|
| Public/user | authenticated API only | NO | NO | NO |
| API service UID | authorized API/DB queries | scoped YES | NO | NO |
| Gateway service UID | NO | accept/listen | NO without authenticated bridge | NO |
| Broker service UID | NO user DB | NO | YES | limited runtime controls ONLY |
| Parser UID (65532) | NO | NO | NO | NO |

**Peer credentials alone are not end-user authorization.** API must derive `tenant_id`/`user_id` from a validated session and enforce resource ownership; gateway must reject caller-supplied subject overrides. HMAC keys need secret manager injection, rotation, unique per workload, no logging or raw storage. A compromised API workload with valid HMAC remains dangerous without quotas, abuse protections and tenant-scoped policy.

## F.1 acceptance before marking PASS

- [ ] Two or more actually distinct, dedicated non-root UIDs, verified with `id` and process credentials in an **owned disposable VM**; no sharing of broker runtime capabilities.
- [ ] API cannot read/open docker.sock or broker socket (negative tests); kernel peer identity verified with two separate processes.
- [ ] Permission checks on *real* API-gateway socket with narrowly scoped group and permissions, while broker retains strict 0700/0600.
- [ ] Authenticated gateway-to-broker transfer and network namespace protection, certificate/key handling where appropriate; unauthorized service and replay fail closed.
- [ ] API session-to-user/tenant binding and broker authorization proof; never trust user-supplied IDs.
- [ ] Real fail-closed behavior during gateway/broker outage, rotation and partial reads; replay remains durable across processes.
- [ ] Adversarial evidence in ephemeral runner without actual CVs, Postgres or live services; independent operator signoff.

## Checks — source branch

```bash
cd /workspaces/Job-Agent-SEC-OPS-01
git fetch origin
git pull --ff-only origin feature/sec-ops-01-broker-isolation
source .venv-secops/bin/activate
cd backend
python -m pytest tests/unit/test_gateway_identity.py tests/unit/test_job_admission.py -v
python -m ruff check .
python -m ruff format --check .
python -m mypy
```

**No actual production isolation or transport approval is claimed.**

## Code-level CI evidence (2026-11-04)

At commit `37843c2cf0af259c208482bc27438ea6491c6c32`, [GitHub Actions run 41928660087](https://github.com/Arthur-Levi/Job-Agent/actions/runs/41928660087), backend job completed **SUCCESS**:
- `ruff check .` PASS
- `ruff format --check .` PASS (158 files)
- `mypy` PASS (152 source files)
- `pytest` **402 passed, 21 skipped, 3 xfailed, 1 warning**; log includes `tests/unit/test_gateway_identity.py ..... `.
- Frontend/audit/sandbox-smoke completed SUCCESS; other browser/E2E jobs were still running at the last inspection.

This is **unit-level authentication policy acceptance**, NOT proof of an authenticated cross-UID gateway deployment. E2.2-F.1 operational acceptance remains **PENDING/NO-GO**.

## Operator Codespaces acceptance — 2026-11-04

The operator provided two consecutive local verification runs on the `Job-Agent-SEC-OPS-01` worktree after a successful fast-forward from `abf5ca2` to `ec4cad8`. The last verification was at `ec4cad8`, branch `feature/sec-ops-01-broker-isolation`, tracking and synchronized with origin, with no changes shown by `git status --short --branch`.

Environment: Linux, Python **3.14.2**, pytest 9.2.0, `.venv-secops`. This differs from the GitHub Actions Python 3.12 environment; both results are separately recorded.

```text
E2.2-F.1 test_gateway_identity.py + test_job_admission.py: 21 passed, 1 warning in 0.06s
Ruff lint: All checks passed!
Ruff format: 158 files already formatted
MyPy: Success: no issues found in 152 source files
PYTEST=0 LINT=0 FORMAT=0 MYPY=0
HEAD: ec4cad8
```

The single warning was `StarletteDeprecationWarning` from `fastapi.testclient` / `httpx`. No skipped tests in this 21-test verification. The prior local synthetic preview suite also reported **6 passed, 1 warning**, and its quality checks passed (156 files, MyPy 150 source files) at the earlier `abf5ca2` checkpoint.

**Decision:** E2.2-F.1 **code-level local acceptance PASS**, *not* operational isolation acceptance. No proof of distinct real UIDs, real gateway listener, scoped API-to-gateway socket, durable replay in live gateway transport, gateway-to-broker bridge or denied Docker access. Maintain `503 CV_SANDBOX_REQUIRED`, PR #24 Draft, SEC/OPS Gate 1 **NO-GO**.
