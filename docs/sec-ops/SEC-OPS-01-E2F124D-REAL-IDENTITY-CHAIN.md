# F.1.2.4-D — signed private broker with actual Linux identities

**Current status: CODE VALIDATION IN PROGRESS — OPERATIONAL NO-GO.** No real CVs, public route, production daemon or authorization to enable `resume_broker.py`. This is an additive security layer over F.1.2.4-C. Do not promote on mock/stub evidence.

## Security design

`backend/app/workers/secops_f124d_verified_chain.py` adds an explicitly named **verified** entry point. The broker process cannot accept a request unless its **actual EUID** is the configured broker UID and differs from the gateway UID, and its already-open Unix listener is bound to the named path with socket `0660`, directory `0710`, proper ownership and gateway group. Once accepted, the connection's actual `SO_PEERCRED` (UID and GID) must match the registered gateway workload, not JSON/header claims.

After verifying process/socket/peer identity, the verified entrypoint delegates to `dispatch_synthetic_authenticated` without any injected attestation or executor. That path validates domain-separated broker HMAC, timestamp, replay and strict job envelope, then requires **exactly** one of three self-generated valid synthetic documents for the fixed synthetic subject/tenant, then real runtime isolation attestation (12/12), then the actual bounded `docker run` parser subprocess. No successful result is possible in Codespaces while its parser returns `unconfined`. The response remains only `F124C_ACCEPTED` or `F124C_DENIED` and contains no CV text.

**Important non-goals:** this module does not provision the UIDs/groups, does not launch independent services, does not bind gateway socket permissions on its own, and does not prove that the gateway has no other access to Docker. A genuine three-process operational result must come from an independently managed, single-purpose Linux VM with AppArmor/SELinux enforced. Do not use `sudo` to fake UID separation in Codespaces.

## Code-only tests

`backend/tests/integration/test_secops_f124d_verified_chain.py`: affirmative confirmation only of the current socket's filesystem security metadata and Linux peer-credential measurement. Negative tests reject same-UID gateway, incorrect broker UID, socket path spoofing, world-accessible socket/directory, mismatched group, missing socket and unregistered live peer. **No fake executor is injected into the verified entrypoint.** The one end-to-end local test intentionally returns DENIED before parsing because the Codespaces test client does not possess a separate gateway UID. That is expected and is not a full-chain PASS.

Run:
```bash
cd /workspaces/Job-Agent-SEC-OPS-01
git fetch origin
git pull --ff-only origin feature/sec-ops-01-broker-isolation
source backend/.venv-f124/bin/activate
cd backend
python -m pytest tests/integration/test_secops_f124d_verified_chain.py -v
python -m pytest tests/integration/test_secops_f124c_private_socket.py -v
python -m pytest tests/integration/test_secops_f124b_broker_parser.py -v
python -m ruff check .
python -m ruff format --check .
python -m mypy
```

## Operational acceptance still required (do not mark PASS without evidence)

1. Provision fresh non-production Ubuntu VM under our control; separate **non-root** OS identities for gateway and broker. Verify `id`, `getent passwd`, `getent group`, socket directory ownership and mode; ensure the gateway has no Docker daemon/socket authority, and broker permission to Docker is narrowly controlled and audited. Do not add gateway to Docker group, nor run API as root.
2. Prepare **broker-owned 0710** socket parent with gateway-group ownership; **0660** socket. Prepare a separate **broker-owned 0700** replay-store directory with SQLite `0600` and controlled retention. Confirm no symlink or world access. Do not place network listener or API secrets in the parser.
3. Use independently provisioned, randomized HMAC workload key **stored privately** (not environment dump or Git); configure the gateway registration and broker identity from trusted operator configuration, not job content. Positive signed request with unique nonce must authenticate via kernel peer credentials; changed signature, wrong UID, wrong GID, old timestamp and duplicate nonce must be rejected, including after broker restart.
4. Run F.1.2.4-VM parser 12/12 first with AppArmor/SELinux **enforcing** and verified effective per-container process profile; image digest recorded, network disabled, read-only root, non-root UID, seccomp, dropped capabilities and limits. Stop if `unconfined`.
5. Run actual gateway → broker private Unix socket → **real** isolated Docker parser with only generated fixtures, **no stub executor** or bypassed attestation. Include timeout, parser crash, socket disconnect, saturated concurrency and cleanup checks. Record PIDs, actual UIDs/GIDs (avoid credentials), response codes, timestamps, image digest and test artifact hashes.
6. Do not claim authorization for production until tenant membership/consent, durable distributed quotas/idempotency/cancel/recovery, retention/LGPD, key rotation, deployment separation, abuse cases, audit and independent Gate 1 signoff pass.

**Release:** PR #24 Draft, SEC/OPS Gate 1 NO-GO, public `503 CV_SANDBOX_REQUIRED` unchanged. Preserve F.1.2.3 checkpoint. No actual candidate documents in this mission.
