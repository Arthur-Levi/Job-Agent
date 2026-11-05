# SEC/OPS E2.2-F.1.2 — Synthetic authenticated gateway-to-broker transport

**Status:** implementation/test candidate, not deployable. PR #24 Draft; Issue #23; SEC/OPS Gate 1 NO-GO; keep `503 CV_SANDBOX_REQUIRED`.

## Principle
The E2.2-F.1.1 probe verified real Linux cross-UID socket permissions but the broker's private directory/socket remain `0700/0600`, deliberately inaccessible to the gateway. **No bridge must bypass these permissions**, share the broker UID, or grant API/gateway docker.sock access. A separate broker-owned acceptor/service transport is needed before deployment.

## New implementation (pure synthetic, not wired into live API/broker)
- `backend/app/workers/broker_transport_auth.py`: domain-separated `jobagent-gateway-broker-v1` HMAC SHA-256 over timestamp, nonce and request digest, binding a **registered gateway service_id + kernel SO_PEERCRED UID/GID**, strict pre-existing job envelope validation, bounded bytes/clock skew, atomic replay-store dependency, and opaque rejection codes. An API-admission signature cannot be reflected/reused for broker admission because the HMAC domains differ.
- `backend/app/workers/broker_transport_wire.py`: length-prefixed, bounded and explicitly typed JSON transport for synthetic Unix socket pair, with exact-field checking and duplicate-key rejection. The receiver authenticates before returning a **metadata-only** result; never imports/executes the CV parser.
- `backend/tests/unit/test_broker_transport_auth.py`: authorized workload, wrong service identity, wrong peer identity, bad signature/tampering, expired/future timestamps, nonce replay and HMAC domain separation.
- `backend/tests/integration/test_synthetic_gateway_broker_wire.py`: send one signed synthetic job over a real Unix `socketpair`, synthetic receiver returns only a digest; replayed message and tampered transport denied; oversized frame rejected before reading body.

**Important:** socketpair tests in the same Unix account **do not demonstrate actual cross-UID forwarding or an authenticated live transport**. E2.2-F.1.1 independently demonstrated permission separation; F.1.2 tests crypto and strict framing. They must be combined with a real broker-owned IPC endpoint and independent OS identities before operational approval.

## Contract
1. API creates an envelope from its authenticated session. It must not accept caller-submitted tenant/user IDs as authority.
2. Gateway validates source peer UID/GID and API HMAC using `GatewayIdentityGate` and `AdmissionService`.
3. Gateway generates a fresh timestamp+nonce, **signs a new message with a distinct broker transport key**, forwards over a separately authenticated broker-controlled channel; the existing private broker socket is not the gateway's client entry point.
4. Broker-side acceptor verifies gateway peer UID/GID **and** HMAC, timestamp, replay and schema, then applies tenant authorization and durable quota/lease policy before any parser work. **This acceptor is not yet implemented.**
5. Signed acknowledgements, durable replay/nonce store, key management/rotation, cancellation/idempotency, handling of partial reads/timeouts and no-PHI logs must be added before live CV traffic.

## Security limitations
- Current `MemoryAdmissionStore` is suitable only for synthetic unit/integration tests; process restarts clear replay state. A PostgreSQL-backed or otherwise atomic durable implementation must be proven on a disposable DB.
- HMAC establishes **workload** identity, not end-user ownership. Production must independently authorize tenant and user.
- No actual broker worker, Docker, parser or customer CV was connected or started.
- The lab is not an authorization to disable `CV_SANDBOX_REQUIRED`.

## Developer checks

```bash
cd /workspaces/Job-Agent-SEC-OPS-01
git fetch origin
git pull --ff-only origin feature/sec-ops-01-broker-isolation
source .venv-secops/bin/activate
cd backend
python -m pytest tests/unit/test_broker_transport_auth.py tests/integration/test_synthetic_gateway_broker_wire.py -v
python -m ruff check .
python -m ruff format --check .
python -m mypy
```

**F.1.2 PASS is limited to code contract and synthetic transport tests**; operational F.1.2 requires broker-owned cross-UID authenticated endpoint, distributed replay protection, adversarial runner evidence and human signoff.

## CI evidence — synthetic transport contract

At commit `2274b8179c6ed3dcf70350bddaf5bff76102312c`, [GitHub Actions run #41941958986](https://github.com/Arthur-Levi/Job-Agent/actions/runs/41941958986), **backend job SUCCESS**:
- `ruff check .` PASS; `ruff format --check .` PASS (163 files);
- `mypy` PASS (156 source files);
- `pytest` **416 passed, 21 skipped, 3 xfailed, 1 warning**, including the new `test_synthetic_gateway_broker_wire.py` (3 tests) and `test_broker_transport_auth.py` (11 tests).
- Audit, frontend, sandbox-smoke, browser-smoke also completed SUCCESS; real-browser-postgres-e2e was still in progress at evidence capture.

**Acceptance:** signed **in-process/socketpair prototype** and fail-closed regression matrix PASS. A live authenticated gateway-to-broker service pair across real UIDs, real packet/session-level authorization, durable nonce store and operational restart/abuse validation **remain NO-GO**.
