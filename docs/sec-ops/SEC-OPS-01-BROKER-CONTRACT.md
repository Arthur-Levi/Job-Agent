# SEC-OPS-01 — Broker Isolation Contract

Status: DRAFT / NO-GO
Base: D2-E2 checkpoint 69c78fc
Tracking: GitHub Issue #23

## 1. Objective

Isolate untrusted resume parsing from the public API,
PostgreSQL, application credentials and host runtime.

## 2. Public API

- Must not access the Docker daemon or Docker socket.
- Must not execute arbitrary container commands.
- May submit only authenticated, bounded parsing requests.
- Must enforce user authorization and request-size limits.
- Must fail closed when the broker is unavailable.
- Must not log resume contents or credentials.

## 3. Broker

- Must run under a separate operational identity.
- Must use a restricted communication channel.
- Must not accept arbitrary images, mounts or commands.
- Must enforce bounded concurrency and deadlines.
- Must support cancellation and resource cleanup.
- Must enforce global and per-user admission controls.
- Must not expose a public TCP listener.
- Must not log personal document contents.
- Must not expose unrestricted host runtime authority.

## 4. Parser

- Runs under a non-root identity.
- Has no outbound network access.
- Uses a read-only root filesystem.
- Has bounded CPU, memory, PIDs and temporary storage.
- Receives no database or application credentials.
- Returns bounded, validated structured output.
- Must terminate when the execution deadline expires.

## 5. Deployment

- Separate API and broker identities.
- No Docker socket mounted into the public API.
- Independently restricted parser runtime.
- Verified filesystem and socket permissions.
- Defined broker lifecycle and supervision.
- Verified security policies on the deployment host.
- Explicit operational monitoring and recovery procedures.

## 6. Acceptance Tests

- API cannot control the container runtime.
- Unauthorized broker requests are rejected.
- Network access from the parser is denied.
- Filesystem restrictions are enforced.
- CPU, memory and process limits are verified.
- Concurrent requests respect global quotas.
- Timeouts terminate parser jobs.
- Cancellations release resources.
- Broker failures do not expose sensitive data.
- Recovery does not leave orphaned workloads.
- Logs do not contain personal documents.

All operational tests must use synthetic data
in an isolated disposable environment.

## 7. Prohibited Operations

- No production deployment before approval.
- No real resumes during pre-beta security testing.
- No Docker daemon access from the public API.
- No tests against preserved PostgreSQL databases.
- No automatic merge into main.
- No removal of CV_SANDBOX_REQUIRED without approval.

## 8. Current Decision

SEC-OPS Gate 1: NO-GO.

The existing production protection
CV_SANDBOX_REQUIRED must remain enabled.

This document is a security contract,
not evidence that the controls are implemented.
