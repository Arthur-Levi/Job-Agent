# Job Agent — E2.2-F.1.2.4-VM: controlled parser operational acceptance

**State:** RUNBOOK READY — **OPERATOR VM RESULT PENDING / NO-GO**. This is NOT a production release, and no real CV uploads are authorized. The previous F.1.2.3 lab checkpoint is preserved at `checkpoint/secops-f123-2026-11-05`.

## Why a separate VM

Codespaces operator evidence: the kernel advertises AppArmor (`Y`), Docker reports `AppArmorProfile=docker-default`, yet `/proc/self/attr/current` inside the restricted parser container, including with explicit `--security-opt apparmor=docker-default`, returned `unconfined`. The parser lab correctly returned `SECOPS_RUNTIME_UNVERIFIED` / `F124_EXIT=1`. Do not weaken the LSM requirement or alter a shared Codespaces host to force a pass.

## Scope & acceptance

- Use a **fresh, single-purpose, non-production Linux VM** (Ubuntu Server 24.04 LTS, amd64, recommended 2 vCPUs/4 GiB RAM/25+ GiB disk), with admin access to its **own kernel and Docker daemon**, not another unprivileged Docker-in-Docker container. Network access is permitted on the **VM host** for OS packages, Git and building the image, but the parser **container must have `--network=none`**.
- No database, API, real-person CVs, secrets, application deployment, public HTTP port, mounted Docker socket or documents from clients.
- Limit SSH access to an authorized source IP. Do not add the operator user to the privileged Docker group; use `sudo docker` or a carefully controlled temporary root acceptance session. Do not print credentials/tokens.
- Check that effective confined profile is visible **inside** the process; daemon `docker info` or `docker inspect` labels alone do not count.
- **PASS only if** the 12 code-enforced checks return `true` with `status=PASS` and `F124_EXIT=0`, plus independent host/runtime evidence and no orphan lab containers. Otherwise **NO-GO**.

## Phase A — prerequisite on the new VM

1. Provision an Ubuntu 24.04 LTS VM with an administrator and SSH access restricted to the operator; do not use any production node.
2. Check its kernel/AppArmor and install basic tools:

```bash
cat /etc/os-release
uname -a
cat /sys/module/apparmor/parameters/enabled
sudo apt-get update
sudo apt-get install -y ca-certificates curl git python3.12 python3.12-venv apparmor apparmor-utils
sudo aa-status
```

3. Install Docker Engine from the **official Docker Ubuntu apt repository**, not the convenience `curl | sh` installer. Follow https://docs.docker.com/engine/install/ubuntu/ (package commands may evolve). The canonical commands at planning time:

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl is-active docker
sudo docker info --format '{{json .SecurityOptions}}'
```

**Stop/no-go:** `apparmor` disabled, `docker info` missing seccomp or AppArmor, `aa-status` unable to demonstrate loaded enforced profiles, or Docker daemon remote/production.

## Phase B — immutable source and local dependencies

Use authenticated GitHub SSH/HTTPS checkout already configured without exposing a token. Do not paste tokens into commands or logs. Start with the fixed, reviewed commit SHA for the acceptance (replace the placeholder with the **exact** commit shown by GitHub after the runbook is accepted).

```bash
git clone git@github.com:Arthur-Levi/Job-Agent.git
cd Job-Agent
git fetch origin feature/sec-ops-01-broker-isolation
git checkout --detach origin/feature/sec-ops-01-broker-isolation
git rev-parse HEAD
git status --porcelain
cd backend
python3.12 -m venv .venv-f124
. .venv-f124/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m pytest tests/unit/test_secops_synthetic_parser_lab.py -v
```

For an actual reproducible security acceptance, record all package versions and the resulting image digest. The existing Dockerfile and Python project still use semver ranges and the base image tag is mutable; **do not promote the image to production without pinned, verified dependencies**.

## Phase C — image build and proof of effective confinement

```bash
sudo docker build -f Dockerfile.resume-parser -t job-agent-resume-parser:d2e2d1 .
sudo docker image inspect job-agent-resume-parser:d2e2d1 --format 'Image={{.Id}} User={{.Config.User}}'
sudo docker info --format '{{json .SecurityOptions}}'
sudo aa-status
```

Execute an isolated, synthetic, read-only process diagnostic:

```bash
sudo docker run --rm --pull never \
  --network none --read-only --cap-drop ALL \
  --security-opt no-new-privileges --security-opt apparmor=docker-default \
  --pids-limit 32 --memory 1g --memory-swap 1g --cpus 1 \
  --user 65532:65532 \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=16m \
  --entrypoint /bin/sh job-agent-resume-parser:d2e2d1 -c \
  'grep -E "^(Uid|CapEff|NoNewPrivs|Seccomp):" /proc/self/status; cat /proc/self/attr/current; ls /sys/class/net'
```

Expect non-root UID `65532`, `CapEff=0`, `NoNewPrivs=1`, `Seccomp=2`, a **confined and enforced** AppArmor profile (e.g., `docker-default (enforce)`) and only `lo`. **STOP** if `unconfined`, AppArmor disabled or the profile is inaccessible.

## Phase D — 12/12 synthetic acceptance

The parser probe currently invokes `docker` itself. On this **dedicated development VM only**, run the already installed venv Python as root so it can reach the VM-local Docker daemon. Do not do this on the Codespaces host or a production host; do not copy credentials into root's environment. The probe's own Docker containers retain non-root UID and all Docker restrictions.

```bash
cd ~/Job-Agent/backend
sudo env SECOPS_F124_ACK=I_OWN_THIS_SYNTHETIC_PARSER_LAB \
  "$PWD/.venv-f124/bin/python" scripts/secops_f124_parser_probe.py
result=$?
echo "F124_EXIT=$result"
sudo docker ps -a --filter name=jobagent-f124
```

Required checks (all `true`):

- Runtime: `NON_ROOT_UID`, `CAPABILITIES_DROPPED`, `NO_NEW_PRIVILEGES`, `SECCOMP_FILTER`, `LSM_CONFINED`, `NETWORK_LOOPBACK_ONLY`.
- Synthetic files: `fictional.txt`, `fictional.pdf`, `fictional.docx`, `bad-header.pdf`, `bad-archive.docx`, `binary.txt`.

**PASS:** all 12 `true` + `status=PASS` + `F124_EXIT=0` + no leftover parser containers. **NO-GO** for any other result. Do not loosen flags, grant `--privileged`, mount `docker.sock`, disable AppArmor, substitute real documents or treat a failed/unknown runtime as PASS.

## Phase E — preserve evidence and decision

Record in `docs/sec-ops/SEC-OPS-01-E2F124-PARSER-SANDBOX.md`: VM OS/kernel, Docker Engine version, `sudo aa-status`, exact Git commit SHA, image SHA-256 ID, effective `/proc/self/attr/current`, all 12 boolean checks, `F124_EXIT`, absence of orphaned containers, errors and remediation if any. Never log document content, credentials or personally identifying data. Commit results and create an immutable checkpoint branch **only after** the full operational evidence passes.

After this lab PASS, the **full F.1.2.4 integration still remains pending**: actual broker-owned authenticated execution of the isolated parser, cgroup/LSM policy validation beyond the six checks, malicious-file robustness, crashes/timeouts/cancel/recovery, production Docker authority separation, durable quotas, authorization by tenant, consent/LGPD and human confirmation. **SEC/OPS Gate 1 remains NO-GO; PR #24 Draft; `503 CV_SANDBOX_REQUIRED` unchanged.**

Official references: https://docs.docker.com/engine/install/ubuntu/ , https://docs.docker.com/engine/security/apparmor/ , https://ubuntu.com/server/docs/security-apparmor/
