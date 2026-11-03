"""Synthetic-only worker supervisor. NEVER passes untrusted resume input to a subprocess.

This is process lifecycle coordination, not a container/VM security boundary.
Use only fixed, reviewed argv. In particular, this module must not be wired to
the real CV parser or API before SEC/OPS security acceptance.
"""

import os
from contextlib import suppress
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Literal, Protocol

from app.workers.job_admission import AdmissionRejected
from app.workers.worker_lease import WorkerLease


class LeaseHeartbeat(Protocol):
    def heartbeat(self, lease: WorkerLease) -> bool: ...

    def finish(self, lease: WorkerLease, *, succeeded: bool) -> bool: ...


@dataclass(frozen=True)
class SupervisionResult:
    outcome: Literal["succeeded", "failed", "revoked", "timeout"]
    returncode: int | None


class SyntheticSupervisor:
    """Run exactly one fixed Python synthetic workload; fail closed on lease loss."""

    def __init__(
        self,
        store: LeaseHeartbeat,
        *,
        poll_seconds: float = 0.1,
        max_seconds: float = 5.0,
        terminate_grace_seconds: float = 0.3,
    ) -> None:
        if (
            not 0.02 <= poll_seconds <= 1.0
            or not 0.1 <= max_seconds <= 30.0
            or not 0.05 <= terminate_grace_seconds <= 2.0
        ):
            raise ValueError("invalid supervisor limits")
        self._store = store
        self._poll = poll_seconds
        self._maximum = max_seconds
        self._grace = terminate_grace_seconds

    def run(
        self, lease: WorkerLease, *, synthetic_mode: Literal["exit", "sleep"] = "exit"
    ) -> SupervisionResult:
        if synthetic_mode not in {"exit", "sleep"}:
            raise ValueError("only reviewed synthetic work is supported")
        # Avoid spawning anything unless current lease is verified.
        try:
            authorized = self._store.heartbeat(lease)
        except AdmissionRejected:
            authorized = False
        if not authorized:
            return SupervisionResult("revoked", None)

        # Fixed source, no shell, no CV bytes, no network or user-supplied argv.
        script = "import time; time.sleep(30)" if synthetic_mode == "sleep" else "pass"
        proc = subprocess.Popen(
            [sys.executable, "-I", "-c", script],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            env={"PATH": os.defpath},
            start_new_session=(os.name == "posix"),
        )
        deadline = time.monotonic() + self._maximum
        try:
            while True:
                # Always verify ownership before accepting a completion.
                try:
                    authorized = self._store.heartbeat(lease)
                except AdmissionRejected:
                    authorized = False
                if not authorized:
                    self._terminate(proc)
                    return SupervisionResult("revoked", proc.returncode)
                code = proc.poll()
                if code is not None:
                    try:
                        finished = self._store.finish(lease, succeeded=(code == 0))
                    except AdmissionRejected:
                        finished = False
                    if not finished:
                        return SupervisionResult("revoked", code)
                    return SupervisionResult("succeeded" if code == 0 else "failed", code)
                if time.monotonic() >= deadline:
                    self._terminate(proc)
                    # Do not mark an uncertain timeout as succeeded.
                    with suppress(AdmissionRejected):
                        self._store.finish(lease, succeeded=False)
                    return SupervisionResult("timeout", proc.returncode)
                time.sleep(self._poll)
        finally:
            if proc.poll() is None:
                self._terminate(proc)

    def _terminate(self, proc: subprocess.Popen[bytes]) -> None:
        if proc.poll() is not None:
            return
        try:
            if os.name == "posix":
                os.killpg(proc.pid, signal.SIGTERM)
            else:
                proc.terminate()
        except ProcessLookupError:
            return
        try:
            proc.wait(timeout=self._grace)
        except subprocess.TimeoutExpired:
            try:
                if os.name == "posix":
                    os.killpg(proc.pid, signal.SIGKILL)
                else:
                    proc.kill()
            except ProcessLookupError:
                pass
            proc.wait(timeout=2.0)
