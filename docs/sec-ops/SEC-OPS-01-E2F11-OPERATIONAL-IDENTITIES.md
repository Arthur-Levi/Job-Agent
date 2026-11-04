# SEC/OPS E2.2-F.1.1 — Linux cross-UID socket boundary probe

**Status 2026-11-04: partial operational proof on a separate disposable Linux sandbox; acceptance of deployed Job Agent remains PENDING.** PR #24 Draft, Issue #23 SEC/OPS Gate 1 NO-GO, keep `503 CV_SANDBOX_REQUIRED`.

## Goal and scope

Advance from prior single-process `socketpair` identity unit tests to *real distinct Linux processes running under different effective UIDs*. Prove a temporary gateway-style Unix socket can be reached by an API identity while a private broker socket cannot, without granting Docker authority. The harness does **not** parse CVs, access a DB, contact a network service, start Docker, or modify actual API/broker services.

## Artifact

`backend/scripts/secops_f111_identity_probe.py` is a standalone Python stdlib harness for a **disposable Linux environment only**, requiring root privileges in that disposable environment and the explicit `SECOPS_DISPOSABLE_ACK=I_OWN_THIS_DISPOSABLE_SANDBOX` acknowledgement. It refuses non-Linux, missing acknowledgement, non-root or locally registered test UIDs. Uses a unique temporary directory and removes it after execution.

Synthetic identities (only numeric IDs local to the disposable runner):
- API: UID **61001**, GID **61010**.
- Gateway: UID **61002**, GID **61010**.
- Broker: UID **61003**, GID **61003**.
- Unauthorized service: UID/GID **61004**.

The broker directory/socket are `0700`/`0600`; the gateway directory/socket are `0770`/`0660` under a deliberately scoped API/gateway group, never world-writable. The gateway service checks peer credentials via Linux `SO_PEERCRED` on accepted sockets.

## Observed isolated-lab result (NOT the Job Agent Codespaces)

In this assistant's isolated container, Linux root capable of starting disposable child processes with unregistered test UIDs, the original local copy of this probe completed with `status: PASS`. Checks:

```json
{
  "API_TO_BROKER_DENIED": true,
  "API_TO_GATEWAY": true,
  "BROKER_DIRECTORY_MODE": true,
  "BROKER_SOCKET_MODE": true,
  "DISTINCT_SERVICE_UIDS": true,
  "GATEWAY_SOCKET_MODE": true,
  "GATEWAY_TO_BROKER_DENIED": true,
  "UNAUTHORIZED_TO_GATEWAY_DENIED": true
}
```

This is a proof of the **OS permissions + real separate-process peer-identity behavior** in that isolated environment. The version committed to GitHub is semantically equivalent but formatting-adjusted. A new run against the committed version must be observed for full verification.

## Manual operator acceptance on an OWNED DISPOSABLE VM/CONTAINER ONLY

Do NOT run this as root on the persistent Codespaces host or on a machine containing customer data. Create a new disposable VM/container whose root does not have access to the host Docker socket, production volumes or credentials. Copy or clone the repository only in that isolated VM. Verify that disposable identity numbers are unused and execute:

```bash
cd backend
SECOPS_DISPOSABLE_ACK=I_OWN_THIS_DISPOSABLE_SANDBOX \
  python scripts/secops_f111_identity_probe.py
```

Run inside disposable root-controlled guest (e.g., a dedicated CI job with its own unprivileged user namespace if supported). Expect one JSON line with `status=PASS` and all eight checks true. Refuse to run if the guard fails. The script does not install new system users/groups, make global permission changes or interact with actual Docker.

## NOT demonstrated / remaining E2.2-F.1.1 gates

- [ ] The GitHub-committed harness passes Ruff/format/MyPy and operator-run disposable validation.
- [ ] Real Job Agent API, gateway and broker deploy as separate actual service identities with verified entrypoints.
- [ ] An API process cannot open any live Docker or container-runtime socket; absence of a socket alone does not establish robust runtime isolation.
- [ ] The gateway-to-broker bridge is independently authenticated without weakening the broker's private socket or sharing IDs.
- [ ] Real API session identity/tenant authorization, HMAC secrets rotation and durable replay protection across process restarts.
- [ ] Failure handling, malformed frames, rate limits, resource caps, namespace restrictions, logs without personal documents and adversarial evidence.
- [ ] Independent operator sign-off with environment and commit attestations.

**Decision:** provisional **OS-socket isolation lab PASS**, E2.2-F.1.1 deployed **NO-GO**, overall Gate 1 **NO-GO**. This test does not authenticate messages at the synthetic gateway; signed-envelope authentication remains covered separately by `gateway_identity.py` and its unit tests, not by this probe.
