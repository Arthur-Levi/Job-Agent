# E2.2-F.1.2.4 — Synthetic PDF/DOCX/TXT parser sandbox: controlled acceptance

**Status:** new synthetic parser lab code and unit tests; **operational acceptance requires operator evidence**. This checkpoint does **NOT** authorize real customer CVs or connect the parser to public upload. `503 CV_SANDBOX_REQUIRED`, PR #24 Draft and SEC/OPS Gate 1 **NO-GO** remain in force.

## Starting point

F.1.2.3 was accepted as a synthetic, real 3-process/3-UID authenticated IPC lab, with 11/11 checks and `F123_EXIT=0`, preserved at `checkpoint/secops-f123-2026-11-05`. The old `app.workers.resume_broker` receives a different, unauthenticated private protocol and is **not wired** to F.1.2.3. Do not expose it to the API.

Existing parser implementation:
- `backend/app/workers/resume_parser.py`: entrypoint with Linux RLIMIT controls.
- `backend/app/services/resume_preview.py`: PDF, DOCX, TXT text extraction and human-review preview.
- `backend/app/services/resume_worker.py`: Docker command with `--network=none`, `--read-only`, `--cap-drop=ALL`, `--security-opt=no-new-privileges`, `--user=65532:65532`, `--memory=1g`, `--cpus=1`, `--pids-limit=32`, tmpfs, 10-second wall limit and limited stdout.
- `backend/Dockerfile.resume-parser`: dedicated parser image; it does not contain API service credentials.

## New artifacts

1. `backend/app/workers/secops_synthetic_parser_lab.py`
   - Generates **three valid synthetic files** entirely in memory: `fictional.txt`, `fictional.pdf`, `fictional.docx`.
   - Generates **three malformed synthetic files** for parser rejection: invalid PDF structure, broken DOCX archive and binary TXT.
   - Checks Docker host-advertised seccomp plus AppArmor or SELinux; rejects unverified or unconfined configuration.
   - Inspects Linux kernel process fields **inside** a separate parser container: non-root UID 65532, zero effective capabilities, `NoNewPrivs=1`, `Seccomp=2`, non-unconfined LSM context, only loopback interface.
   - Uses existing restricted `_container_command` and bounded `_run_bounded` to process the six synthetic documents. Never mounts a host CV or DB and never transmits user files to the parser.
   - Ensures `_cleanup_container` even on parser timeout or failure. Prints only boolean checks via the CLI.
2. `backend/tests/unit/test_secops_synthetic_parser_lab.py`: validates generated documents with real PDF/DOCX/TXT extraction, runtime attestation rejection matrix, explicit opt-in, synthetic executor contract and container cleanup; **unit tests do not invoke Docker**.
3. `backend/scripts/secops_f124_parser_probe.py`: operator-only opt-in CLI, returns JSON check matrix and exit status.

**Limits of proof:** Runtime attestation proves only the **specific disposable parser process** tested; it is not proof of Docker authority isolation at the application host, a complete LSM/seccomp policy review or production deployment. Docker default seccomp and LSM enforcement must be audited. The presence of Docker host security options alone is not sufficient, hence the in-container kernel checks.

## P0 prerequisite — prepare the parser image on an isolated development daemon

The parser image must be built only on a disposable/nonproduction Docker daemon. It currently uses network-based dependencies during image build, and the Dockerfile uses version ranges; lock dependencies and image digest before an actual beta.

Do **not** mount real CVs, the application's database, secrets or `/var/run/docker.sock` into any parser container.

```bash
cd /workspaces/Job-Agent-SEC-OPS-01
git status --short --branch
git fetch origin
git pull --ff-only origin feature/sec-ops-01-broker-isolation
source .venv-secops/bin/activate
cd backend
python -m pytest tests/unit/test_secops_synthetic_parser_lab.py -v
python -m ruff check .
python -m ruff format --check .
python -m mypy
```

Build the local image (developer-controlled daemon, not production):

```bash
cd /workspaces/Job-Agent-SEC-OPS-01/backend
docker build -f Dockerfile.resume-parser -t job-agent-resume-parser:d2e2d1 .
docker image inspect job-agent-resume-parser:d2e2d1 --format '{{.Id}}'
```

Run operator evidence (from repository backend; **no uploaded data**):

```bash
export SECOPS_F124_ACK=I_OWN_THIS_SYNTHETIC_PARSER_LAB
python scripts/secops_f124_parser_probe.py
result=$?
unset SECOPS_F124_ACK
echo "F124_EXIT=$result"
```

Expected JSON fields: `NON_ROOT_UID`, `CAPABILITIES_DROPPED`, `NO_NEW_PRIVILEGES`, `SECCOMP_FILTER`, `LSM_CONFINED`, `NETWORK_LOOPBACK_ONLY`, `fictional.txt`, `fictional.pdf`, `fictional.docx`, `bad-header.pdf`, `bad-archive.docx`, `binary.txt` — **12/12 true**, `status=PASS`, `F124_EXIT=0`.

**No-GO** if Docker info lacks seccomp/LSM, kernel says unconfined or lacks seccomp, test output is malformed, any parser crashes, cleanup fails or any document not parsed/rejected as expected. Never add `--privileged`, `seccomp=unconfined`, `--network=host`, relax Docker caps, mount Docker socket or weaken the user identity to force a pass.

## Remaining P0 gates after a 12/12 lab result

- The new parser lab is **not** yet connected to the F.1.2.3 authenticated broker path. Implement the real isolated broker→parser dispatch **only after validating kernel isolation**, authenticated tenant subject, durable quotas and idempotent execution; do not resurrect unauthenticated access through `resume_broker.py`.
- Runtime isolation proof of the *actual production deployment*: Docker authority inaccessible to API/gateway; broker restricted and separate.
- Operational malicious-file suite: PDF xref corruption/embedded scripts, DOCX zip-bomb sizes/path/active content, truncated and oversized files, timeouts, process crashes, queue/cancellation, concurrently submitted documents and restart recovery.
- Verify root filesystem read-only, cgroup CPU/RAM/PID controls and actual LSM/seccomp profile **using separate runtime evidence**, not only launch arguments.
- Audited consent, tenant membership, retention/deletion and LGPD review, secret rotation, logging redaction and human confirmation before storing extracted career facts.
- Independent SEC/OPS Gate 1 signoff before enabling real-person CV processing.


## CI evidence — parser lab policy and synthetic fixtures

Code commit `7a475714190da4ffba838dd356833b20ff40cc71`, [GitHub Actions run #42056025067](https://github.com/Arthur-Levi/Job-Agent/actions/runs/42056025067), backend **SUCCESS**:
- Ruff check PASS; Ruff format PASS (**176 files**).
- MyPy PASS (**166 source files**).
- Pytest **470 passed, 21 skipped, 3 xfailed, 1 warning** (**15 new** parser lab tests).
- Audit, frontend, browser-smoke, sandbox-smoke PASS; real-browser-postgres-e2e still running at evidence capture.
- **Do not label runtime F.1.2.4 PASS** based on CI; the opt-in Docker parser probe does not run in GitHub Actions. The operator must independently provide all twelve true checks + `F124_EXIT=0` from the explicitly controlled Docker environment.


## Operator diagnostic evidence — LSM UNCONFINED, F.1.2.4 NO-GO (2026-11-05)

Operator reported `SECOPS_RUNTIME_UNVERIFIED` and `F124_EXIT=1` from the opt-in F.1.2.4 probe. The follow-up controlled Docker diagnostic reported:

```text
docker info SecurityOptions:
["name=apparmor,profile=default","name=seccomp,profile=builtin","name=cgroupns"]
Docker Engine: 29.8.0-1
Parser image: sha256:c2da0d8d6395d51c66a7da6c4e67c80bd03c3b9a4757ee64f0e9bbff72d82355
Image user: 65532:65532
Inside disposable non-root network-none read-only container:
Uid: 65532 65532 65532 65532
CapEff: 0000000000000000
NoNewPrivs: 1
Seccomp: 2
/proc/self/attr/current: unconfined
/sys/class/net: lo
```

**Technical judgment:** Docker host advertises availability of AppArmor and seccomp, but the operator's actual container had **no active AppArmor confinement** (`unconfined`). This is a **P0 unresolved runtime isolation issue**; the daemon security-options list is not evidence of per-container policy enforcement. `Seccomp: 2` demonstrates syscall filter mode, not an enforced LSM policy. Do not bypass LSM checking, run privileged, or loosen parser identity. The six parser fixture executions were not demonstrated as successful because the attestation failed first.

**Next non-destructive diagnostics:** query `docker inspect` of a live named disposable container for `.AppArmorProfile` and `.HostConfig.SecurityOpt`, compare its `/proc/self/attr/current`, check `/sys/kernel/security/lsm` and host `aa-status` if accessible. A controlled diagnostic can explicitly request `--security-opt apparmor=docker-default` (the Docker-documented default), but failure must remain NO-GO; do not edit Docker daemon settings on the shared Codespaces host. If confined profiles cannot be applied in Codespaces, move the operational parser acceptance to an isolated VM/host with AppArmor/SELinux enforced, while keeping code-only tests here.

**Release:** SEC/OPS Gate 1 NO-GO; `503 CV_SANDBOX_REQUIRED` unchanged; PR #24 Draft. No real CV processing authorized.
