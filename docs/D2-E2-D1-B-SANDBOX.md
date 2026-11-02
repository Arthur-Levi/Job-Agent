# D2-E2.D.1-B — document parser container (pre-beta)

**NOT production approved.** The production endpoint still returns `503 CV_SANDBOX_REQUIRED`.

Build from backend:

```bash
cd backend
docker build -f Dockerfile.resume-parser -t job-agent-resume-parser:d2e2d1 .
```

For synthetic, local tests only, select `RESUME_PARSER_MODE=container` for the API process. The default remains the prior resource-limited subprocess in development and test.

The API invokes a new ephemeral container with `--network=none`, `--read-only`, `--cap-drop=ALL`, `--security-opt=no-new-privileges`, user 65532, a 16 MiB bounded `/tmp` tmpfs, CPU/memory/pid limits, no mounts, no secrets and no published ports. The only data channel is the process' stdin/stdout. The image contains only the parser modules and necessary libraries. Docker's default seccomp policy must be verified on the deployment host; a rootless or otherwise isolated runtime is preferred.

Do not mount the host Docker socket inside a public web-facing API container as an operational solution. Docker API control is host-level power. The current opt-in Docker CLI execution is a **local security-validation prototype** only. A dedicated worker broker/orchestrator with narrowly scoped permissions and verified resource controls is needed before real customer CVs.

No execution of malicious samples or untrusted documents is authorized in the Codespaces host. Use synthetic PDFs/DOCX/TXT and a disposable, isolated test runner.

## Remaining security gates
- Verify default seccomp/AppArmor and runtime isolation; prohibit privileged Docker daemon access from public API.
- An initial process-local bound of two concurrent parsers now rejects overload with `CV_PARSER_BUSY` before spawning. This is **not** a global, distributed or per-user quota: API replicas each have their own capacity. A centralized admission-control layer with per-user limits is required before beta.
- The parent now incrementally reads stdout with a hard 130 KB cap and a monotonic wall deadline. CI must pass on the exact commit before this can be counted as verified.
- Test timeout/kill/cleanup, denied outbound network and inability to read host files via safe probes *inside a disposable container*.
- Ensure no personally identifying information in logs, analytics or exception reports.
- Validate error mapping, memory exhaustion, malformed documents, archive bombs and end-to-end availability.
- Keep production blocked until a separate review authorizes the worker deployment and removes the gate in a subsequent PR.

## D2-E2.D.1-C implementation note

The API-to-Docker path remains an **opt-in development-only prototype**. The upload endpoint still returns `503 CV_SANDBOX_REQUIRED` in production independently of parser mode. Do **not** mount or expose the Docker socket to the public API; any architecture that does so fails security review.

For a production candidate, run parsing behind an independently deployed, narrowly permissioned broker. The API should call only an authenticated, bounded protocol endpoint (not the Docker control API). The broker must enforce an instance-independent global concurrency quota, per-user admission, strict TTL and no ability to mount arbitrary host paths. Workload identity should be restricted to submitting parse jobs and reading their own bounded results. Infrastructure tests must demonstrate network isolation, resource ceilings and cancellation. No code in this PR enables that operational integration.

Local tests added in D2-E2.D.1-C exercise bounded output, overload rejection and release of per-process slots. These are not proof of distributed quotas or production-ready isolation.
