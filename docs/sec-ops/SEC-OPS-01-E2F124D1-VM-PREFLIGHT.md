# SEC/OPS F.1.2.4-D.1 — independent Ubuntu VM preflight

**Status: PREPARATION / NO-GO.** This document is an operator checklist, **not** evidence of a running VM, installed broker daemon, or approved parser. Never accept real CVs; public `503 CV_SANDBOX_REQUIRED` remains active. Do not run these provisioning commands in Codespaces.

## Scope

Fresh independent Ubuntu Server **24.04 LTS VM**, 2 vCPU, 4 GiB RAM, 25+ GiB storage, admin SSH access from a restricted IP; operator-controlled kernel and Docker daemon. No exposed Job Agent/API/database ports; no candidate documents, API secrets, real user data or production tokens. Before creating any OS accounts, verify the VM is independently provisioned and under our administration.

## Phase 1 — host evidence, no changes

```bash
set -eu
echo "=== IDENTITY / OPERATING SYSTEM ==="
hostnamectl
id
cat /etc/os-release
uname -a
echo "=== APPARMOR KERNEL ==="
cat /sys/module/apparmor/parameters/enabled
cat /proc/self/attr/current
echo "=== APPARMOR POLICY ==="
sudo aa-status
echo "=== DOCKER (if installed) ==="
if command -v docker >/dev/null 2>&1; then
  sudo docker version
  sudo docker info --format '{{json .SecurityOptions}}'
fi
echo "=== HOST LISTENERS ==="
sudo ss -lntp
```

The host's *operator shell* might be unconfined; this alone is not a failure, unlike the **parser container's** effective `/proc/self/attr/current`. Do not equate an `AppArmorProfile` label in Docker inspection with proven enforcement.

## Phase 2 — install packages on freshly provisioned VM

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git python3.12 python3.12-venv apparmor apparmor-utils
```

Install Docker Engine only from its [official Ubuntu APT instructions](https://docs.docker.com/engine/install/ubuntu/) and verify its [AppArmor guidance](https://docs.docker.com/engine/security/apparmor/). Do not use the curl-to-shell convenience installer, do not add the gateway to group `docker`, do not expose TCP Docker daemon, and do not share a host daemon with production. Installing Docker does not constitute a sandbox PASS.

## Phase 3 — separate OS identity plan

Provision dedicated non-root *system* accounts `ja_gateway` and `ja_broker` plus dedicated shared group `ja_gateway_ipc`. Gateway account must **never** be in `docker`, `sudo`, or have access to `/var/run/docker.sock`. Group membership enabling a broker to access Docker is effectively root-equivalent: require separately audited, narrowly scoped container launcher before proceeding with an actual parser dispatch. Do not grant unrestricted daemon access simply to force a positive test.

An independently approved lab operator may prepare accounts using these commands on the new VM after confirming they do not already exist:

```bash
sudo groupadd --system ja_gateway_ipc
sudo useradd --system --user-group --no-create-home --shell /usr/sbin/nologin ja_gateway
sudo useradd --system --user-group --no-create-home --shell /usr/sbin/nologin ja_broker
sudo usermod -aG ja_gateway_ipc ja_gateway
id ja_gateway
id ja_broker
getent group ja_gateway_ipc
```

Group membership and UID/GID alone do not prove isolation: the deployment must be configured to run two **actual independent processes** as those users; no `sudo` trick inside Codespaces counts as evidence.

### Private IPC directory

The F124C/D code requires a broker-owned `0710` directory whose group is the gateway IPC group, with broker-owned `0660` socket. It also requires a separate broker-owned `0700` directory for the replay ledger (SQLite mode `0600`).

```bash
sudo install -d -o ja_broker -g ja_gateway_ipc -m 0710 /run/jobagent-f124d
sudo install -d -o ja_broker -g ja_broker -m 0700 /var/lib/jobagent-f124d-replay
sudo stat -c '%U %G %a %n' /run/jobagent-f124d /var/lib/jobagent-f124d-replay
```

**Do not bind a socket or start a parser yet.** The F124D module is currently a callable verification function, **not** a deployable broker/gateway daemon or CLI; a real signed gateway→broker full-process runner, secure key provisioning, broker Docker authority separation and negative abuse acceptance remain to be implemented/reviewed. Do not improvise these components in a privileged shell.

## Phase 4 — existing parser-only 12/12 lab (after Docker installation)

Use [SEC-OPS-01-E2F124-VM-OPERATIONAL-ACCEPTANCE.md](SEC-OPS-01-E2F124-VM-OPERATIONAL-ACCEPTANCE.md), pinned to a reviewed commit, to build and verify the parser-only isolated Docker lab. Inspect the **effective container process** `/proc/self/attr/current`; require enforced AppArmor, six effective kernel checks and six synthetic parser fixture tests. `12/12 PASS` approves only the parser lab, not the real broker chain or SEC/OPS Gate 1.

## NO-GO conditions

- VM kernel/host isolation absent, AppArmor disabled or parser process `unconfined`
- Gateway and broker have the same runtime UID/GID, or no evidence of independent processes
- Group/world access too broad on the socket or replay DB, missing `SO_PEERCRED` checks
- Docker daemon/socket accessible to the gateway, or broker has unaudited root-equivalent Docker authority
- Real CVs, network-enabled parser, injected executor/attestation in a purported operational PASS
- Any signer key committed, printed to logs, or client-provided as identity
- Missing durable replay/restart behavior, timeout/crash cleanup and attack-case results

**Decision:** until positive real-UID HMAC→broker→isolated parser acceptance, negative access tests and VM LSM evidence are all verified, F.1.2.4-D.1 and SEC/OPS Gate 1 are **NO-GO**; PR #24 remains Draft. Never remove `CV_SANDBOX_REQUIRED`.
