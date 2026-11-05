# F.1.2.4-C — separate process, private Unix broker socket (synthetic only)

**Status: CODE / IPC MECHANICS ONLY; operational broker/parser execution NO-GO.**

This checkpoint extends the F.1.2.4-B signed, synthetic-only broker→parser prototype. It **does not** connect the production API, deploy the legacy unauthenticated `resume_broker.py`, or change `503 CV_SANDBOX_REQUIRED`. No real-person documents or production jobs.

## Files

- `backend/app/workers/secops_f124c_private_socket.py`: one-shot Unix filesystem listener; requires root-absolute socket path under a pre-existing **broker-owned 0710 directory**, directory group matching trusted gateway group, and socket `0660` owned by real broker UID and gateway group. Existing target/symlink denied rather than unlinked. Broker runtime `os.geteuid()` must equal the configured broker UID; gateway UID must be distinct. One accepted request, 3-second socket timeout, bounded response, opaque accept/deny, and dispatch through `dispatch_synthetic_authenticated` by default (SO_PEERCRED + HMAC + nonce + synthetic allowlist + operational attestation).
- `backend/tests/integration/test_secops_f124c_private_socket.py`: mechanically tests a **real second Linux process** and a private filesystem socket, socket mode, failure to bind in a world-accessible directory, symlink/existing file, UID mismatch, absent listener, timeout, opaque rejection, same UID fail-closed and oversized response.

## Very important limits of the tests

The POSITIVE separate-process test injects a **stub dispatch** and uses the same local OS UID for its process and client. It proves **only actual separate process and Unix socket mechanics**; it **does not** prove genuine broker/gateway UID separation, HMAC/nonce verification, or parser/container runtime confinement. The default (non-stubbed) dispatcher retains those security checks and must refuse the known unconfined Codespaces runtime. Do not claim full F.1.2.4-C PASS from a stub-based test.

For a genuine operator test, provision a dedicated VM with different OS accounts for gateway and broker, a broker-owned 0710 directory and 0660 socket with explicitly authorized gateway group, least-privilege credentials and dedicated private signed HMAC secret, durable replay and a confined parser image. Validate the **real effective** UID/GID, SO_PEERCRED, 12/12 LSM/AppArmor test, parser image digest, and no broad socket access. Test denied unauthorized service IDs/UIDs, modified signature, nonce replay, oversized frames and parser timeout/cleanup under the actual process architecture. The lab's Python prototype is **not a production daemon** and has no production process supervision, distributed queue, quotas, cancellation or persistent job admission.

## Codespaces verification (no Docker / no real CV)

```bash
cd /workspaces/Job-Agent-SEC-OPS-01
git fetch origin
git pull --ff-only origin feature/sec-ops-01-broker-isolation
source backend/.venv-f124/bin/activate
cd backend
python -m pytest tests/integration/test_secops_f124c_private_socket.py -v
python -m pytest tests/integration/test_secops_f124b_broker_parser.py -v
python -m ruff check .
python -m ruff format --check .
python -m mypy
```

**Gate remains NO-GO** until separate OS identities are actually proven in a controlled Linux VM and all remaining SEC/OPS controls are accepted. `CV_SANDBOX_REQUIRED` must remain in place; PR #24 remains Draft. F.1.2.3 checkpoint immutable.
