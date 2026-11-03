"""Synthetic-only admission proof of concept; no network listener or parser execution.

HMAC authenticates a trusted API workload, NOT the end user. The API must derive
subject fields from its authenticated session, never from untrusted client JSON.
This module uses a single-process memory store; it is NOT a distributed quota,
durable replay store, production authentication service or deployable broker.
"""

import hashlib
import hmac
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID, uuid4

from app.workers.job_protocol import ValidatedJob, validate_job_envelope

MAX_CLOCK_SKEW_SECONDS = 60
MAX_NONCE_CHARS = 96
HMAC_DOMAIN = b"jobagent-worker-admission-v1\n"


class AdmissionRejected(Exception):
    """Opaque, non-PII admission failure."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class AdmissionResult:
    job_id: UUID
    status: str
    reused: bool = False


@dataclass
class _JobRecord:
    owner_user_id: UUID
    owner_tenant_id: str
    fingerprint: bytes
    status: str


class AdmissionStore(Protocol):
    """Store contract used by synthetic admission services."""

    def accept_nonce(self, service_id: str, nonce: str, now: int) -> bool: ...

    def submit(self, job: ValidatedJob) -> AdmissionResult: ...

    def inspect(self, job: ValidatedJob) -> AdmissionResult: ...


class MemoryAdmissionStore:
    """Single-process test store. Never use as a production distributed quota."""

    def __init__(self, *, global_limit: int = 2, user_limit: int = 1) -> None:
        if global_limit < 1 or user_limit < 1:
            raise ValueError("limits must be positive")
        self._global_limit = global_limit
        self._user_limit = user_limit
        self._lock = threading.Lock()
        self._nonces: dict[tuple[str, str], int] = {}
        self._jobs: dict[UUID, _JobRecord] = {}
        self._idem: dict[tuple[str, UUID, str], UUID] = {}

    def accept_nonce(self, service_id: str, nonce: str, now: int) -> bool:
        """Atomically reject repeated nonces within the allowed timestamp window."""
        with self._lock:
            self._nonces = {key: expiry for key, expiry in self._nonces.items() if expiry >= now}
            key = (service_id, nonce)
            if key in self._nonces:
                return False
            self._nonces[key] = now + 2 * MAX_CLOCK_SKEW_SECONDS
            return True

    def submit(self, job: ValidatedJob) -> AdmissionResult:
        if job.operation != "submit" or job.idempotency_key is None:
            raise AdmissionRejected("ADMISSION_INVALID")
        assert job.document is not None
        digest = hashlib.sha256(job.document).digest()
        fingerprint = (
            hashlib.sha256(job.filename.encode("utf-8") + b"\x00" + digest).digest()
            if job.filename is not None
            else digest
        )
        key = (job.tenant_id, job.user_id, job.idempotency_key)
        with self._lock:
            previous = self._idem.get(key)
            if previous is not None:
                record = self._jobs[previous]
                if not hmac.compare_digest(record.fingerprint, fingerprint):
                    raise AdmissionRejected("ADMISSION_CONFLICT")
                return AdmissionResult(previous, record.status, reused=True)
            active = [r for r in self._jobs.values() if r.status in {"queued", "running"}]
            if len(active) >= self._global_limit:
                raise AdmissionRejected("ADMISSION_BUSY")
            per_user = sum(
                1
                for record in active
                if record.owner_tenant_id == job.tenant_id and record.owner_user_id == job.user_id
            )
            if per_user >= self._user_limit:
                raise AdmissionRejected("ADMISSION_BUSY")
            job_id = uuid4()
            self._jobs[job_id] = _JobRecord(job.user_id, job.tenant_id, fingerprint, "queued")
            self._idem[key] = job_id
            return AdmissionResult(job_id, "queued")

    def inspect(self, job: ValidatedJob) -> AdmissionResult:
        if job.job_id is None:
            raise AdmissionRejected("ADMISSION_INVALID")
        with self._lock:
            record = self._jobs.get(job.job_id)
            if (
                record is None
                or record.owner_user_id != job.user_id
                or record.owner_tenant_id != job.tenant_id
            ):
                # Do not distinguish nonexistent from another user's job.
                raise AdmissionRejected("ADMISSION_NOT_FOUND")
            if job.operation == "cancel" and record.status in {"queued", "running"}:
                record.status = "cancelled"
            return AdmissionResult(job.job_id, record.status)

    def complete_for_test(self, job_id: UUID) -> None:
        """Test-only terminal transition; no parser is started."""
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                raise AdmissionRejected("ADMISSION_NOT_FOUND")
            if record.status in {"queued", "running"}:
                record.status = "succeeded"


class AdmissionService:
    """Validates signed envelopes before touching the in-memory test store.

    Signing: HMAC-SHA256(domain || timestamp || newline || nonce || newline ||
    SHA256(raw_envelope)). Keep service secrets out of repositories and logs.
    """

    def __init__(
        self,
        service_keys: dict[str, bytes],
        store: AdmissionStore,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if not service_keys or any(not name or len(key) < 32 for name, key in service_keys.items()):
            raise ValueError("service keys must be at least 32 bytes")
        self._keys = service_keys.copy()
        self._store = store
        self._clock = clock

    @staticmethod
    def signature(key: bytes, raw: bytes, timestamp: int, nonce: str) -> str:
        material = (
            HMAC_DOMAIN
            + str(timestamp).encode("ascii")
            + b"\n"
            + nonce.encode("ascii")
            + b"\n"
            + hashlib.sha256(raw).digest()
        )
        return hmac.new(key, material, hashlib.sha256).hexdigest()

    def admit(
        self,
        raw: bytes,
        *,
        service_id: str,
        timestamp: int,
        nonce: str,
        signature: str,
    ) -> AdmissionResult:
        key = self._keys.get(service_id)
        if key is None:
            raise AdmissionRejected("ADMISSION_UNAUTHORIZED")
        if (
            type(timestamp) is not int
            or abs(self._clock() - timestamp) > MAX_CLOCK_SKEW_SECONDS
            or not isinstance(nonce, str)
            or not 16 <= len(nonce) <= MAX_NONCE_CHARS
            or not nonce.isascii()
            or not nonce.isalnum()
            or not isinstance(signature, str)
            or len(signature) != 64
            or not all(char in "0123456789abcdef" for char in signature)
        ):
            raise AdmissionRejected("ADMISSION_UNAUTHORIZED")
        try:
            expected = self.signature(key, raw, timestamp, nonce)
        except (UnicodeError, ValueError):
            raise AdmissionRejected("ADMISSION_UNAUTHORIZED") from None
        if not hmac.compare_digest(expected, signature):
            raise AdmissionRejected("ADMISSION_UNAUTHORIZED")
        # Validate complete message before allocating a replay-store record.
        try:
            job = validate_job_envelope(raw)
        except ValueError:
            raise AdmissionRejected("ADMISSION_INVALID") from None
        if not self._store.accept_nonce(service_id, nonce, int(self._clock())):
            raise AdmissionRejected("ADMISSION_REPLAY")
        if job.operation == "submit":
            return self._store.submit(job)
        return self._store.inspect(job)
