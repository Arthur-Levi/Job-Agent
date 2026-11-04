# SEC/OPS E2.2-F — Operational worker isolation, staged acceptance

**Status:** P0 / implementation IN PROGRESS; **PRODUCTION NO-GO**. Draft PR #24, Issue #23, `CV_SANDBOX_REQUIRED` remains mandatory.

## Why E2.2-E is insufficient
`SyntheticSupervisor` exercises lease checks with synthetic child processes; `ProtectedOutputStore` fences only digest metadata in disposable PostgreSQL. Neither safely supervises an actual untrusted parser nor prevents external output writes. The existing parser container flags and local Unix socket broker are promising but have not been accepted as an actual multi-identity deployment.

## Current E2.2-F.0 implementation (configuration policy, not isolation)
- `backend/app/workers/secops_deployment_preflight.py`: deterministic, fail-closed configuration contract for independently verified staging deployment evidence. This pure function **cannot verify a host or container** and must not be used as a signoff.
- `backend/tests/unit/test_secops_deployment_preflight.py`: policy regression tests against unsafe modes (API subprocess/container, Docker socket, root identities, missing LSMs, network, insecure socket, PID/memory/CPU limits and logs with document content).
- No API, broker, parser, migrations or production deployment settings changed by this stage.

## Mandatory architecture decisions BEFORE live worker integration
1. **API identity:** non-root, no docker.sock or Docker daemon credentials, no parser process privileges. Must authenticate and authorize requests from sessions with tenant/user isolation. Reject arbitrary user-provided subject IDs.
2. **Broker identity:** daemon privileges isolated from API, separate workload identity and tightly restricted container runtime capabilities; no public TCP port.
3. **Broker socket permissions — OPEN DESIGN ISSUE:** current broker requires socket directory `0700` and socket `0600`. A separately identified API **cannot connect** to that socket unless an explicitly reviewed intermediary, endpoint, or dedicated access mechanism is provided. **Do not chmod socket to 0666, share Docker socket, or force API to run as broker.** Design and test the authentication/access bridge (e.g., small dedicated gateway with authenticated API-to-gateway transport and authorization), keeping Docker privilege solely broker-side.
4. **Parser runtime:** network disabled (not just blocked egress), read-only root, non-root UID, drop all caps, no-new-privileges, seccomp + AppArmor/SELinux on compatible host, bounded pids/RAM/CPU/FS and deadlines. Verify actual container runtime introspection, not just `docker run` argv.
5. **Process lifecycle:** bound one lease to a worker, handle heartbeat failures, cancellation and child process trees, kill/reap, orphan cleanup, quota restoration, idempotent retries and poison queues. Disallow claim takeover until prior parser's external effects are fenced or terminated.
6. **Output:** separate staging object with limited TTL; digest/size verification, authorization + fenced final commit (generation/tenant), immutable object key and cleanup; no parse output leaks to shared logs.
7. **Observability:** redacted structured events, max job queue depth, abuse detection, alerts; no CV names, bodies or signed tokens in logs.
8. **Isolation acceptance:** disposable VM or dedicated runner, owned synthetic CVs only, no access to actual Job Agent DB, tokens or external data; separately test namespace, mount, process, syscall/LSM, network, limits and forced crash.

## Gates
- **F.0:** configuration-policy regression and synthetic preview contracts green in CI. A local policy PASS != real isolation.
- **F.1:** broker/API authentication and socket access blueprint agreed, separate identities verified at runtime.
- **F.2:** container host isolation adversarial acceptance, limits / no network / no secrets proven.
- **F.3:** lease-aware real process supervision; timeout/cancel/orphan recovery/fencing tested with synthetic documents only.
- **F.4:** staged output destination with per-tenant authorization and transactional commit.
- **F.5:** integration E2E, incident/restart recovery and human review, then explicit gate decision.

## Synthetic journey in parallel
`backend/tests/integration/test_synthetic_resume_journey_contract.py` tests the existing `build_preview` in memory with fake TXT/PDF/DOCX and missing data; confirms that previews remain `pending`, detect separate experiences and do not claim official ATS certification. It deliberately does **not** call the unapproved upload API, Fact Ledger DB write, real parser/broker, React browser, or document exporter. The full E2E product acceptance will require those later in a discarded environment after F.1–F.4.

## Local checks after sync
```bash
set +e
cd /workspaces/Job-Agent-SEC-OPS-01
git fetch origin
git pull --ff-only origin feature/sec-ops-01-broker-isolation
source .venv-secops/bin/activate
cd backend
python -m pytest tests/unit/test_secops_deployment_preflight.py tests/integration/test_synthetic_resume_journey_contract.py -v
python -m ruff check .
python -m ruff format --check .
python -m mypy
```

**Never run tests against `jobagent_test`, `react_test`, or real resumes.** These new tests are in-memory and do not connect to PostgreSQL.

## Evidence currently missing
- The proposed new tests have been committed but have not been run locally by the operator until an explicit PASS is received; CI checks may run on push.
- Real deployment architecture, validated runtime identity, authenticated gateway, red-team tests, output object store and production migration **do not exist as approved outcomes**.
- Gate 1 remains **NO-GO**.
