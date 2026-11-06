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


## CI evidence — 2026-11-05

Latest code commit `ee0b63de8d3a0858c0fa56f8f2310bce2c18c75f`, [Actions #42124911343](https://github.com/Arthur-Levi/Job-Agent/actions/runs/42124911343): **backend SUCCESS** (491 passed, 21 skipped, 3 xfailed, 1 warning). New private socket process test module: **10 passed**. Ruff check PASS, Ruff format PASS (180 files), MyPy PASS (170 source files). Audit, sandbox-smoke, frontend and browser-smoke passed; real-browser-postgres-e2e still in progress at capture.

**This is code CI only.** The only positive IPC case intentionally uses a stub dispatch and does not validate actual distinct broker UID, peer identity, signed payload, parser Docker or kernel LSM enforcement. Enforced AppArmor VM deployment proof, genuine broker-to-parser operational attestation and SEC/OPS Gate 1 are **NO-GO**. Never enable real CV intake.


## Local regression reproduction and race correction — 2026-11-05

Operator running code commit `295d894` in Codespaces reported F124D **10 passed**, F124B **11 passed**, Ruff and MyPy PASS, but F124C `test_real_separate_process_unix_ipc_mechanics_only` failed intermittently with `BrokenPipeError` on `send_frame()`. Root cause in test harness: the *stub* dispatcher returned immediately without consuming the client's frame, allowing the broker process to send ACK and close its Unix socket before the client finished writing. It was **not** evidence of a signature failure or a successfully confined runtime. This issue was a regression failure, not a PASS.

Updated only the synthetic IPC test harness to read and validate the full **bounded** test frame before returning its stub ACK, and to drain the expected invalid synthetic frame before its simulated denial; no production socket, auth, parser, LSM or runtime flags changed. Code commits: `a5d0e12`, `a6038d3`.

[GitHub Actions run #42128504227](https://github.com/Arthur-Levi/Job-Agent/actions/runs/42128504227): backend SUCCESS: **501 passed, 21 skipped, 3 xfailed, 1 warning**, including F124C **10 passing**, Ruff lint/format PASS (182 files) and MyPy PASS (172 sources). The operator must re-run the two local F124C/F124D suites to confirm the intermittent Codespaces failure is also resolved locally.

**Security unchanged:** positive F124C test still uses stub, not the actual distinct-UID/authenticated confined parser. SEC/OPS Gate 1 remains NO-GO; `CV_SANDBOX_REQUIRED` unchanged.
