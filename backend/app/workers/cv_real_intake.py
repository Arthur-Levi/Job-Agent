"""E2.2-F.1.2.2: fail-closed CV intake policy for a future LIVE pipeline.

This module intentionally does not parse a CV, open a socket, invoke Docker,
persist bytes or enable public upload. Call ONLY after authentication and a
trusted tenant-membership lookup; NEVER bind subject from user-provided JSON.
"""

import hashlib
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.workers.job_protocol import MAX_DOCUMENT_BYTES, ValidatedJob


class CvIntakeRejected(Exception):
    """Opaque rejection code. No filenames, CV text, or personally identifying data."""

    def __init__(self, code: str = "CV_INTAKE_DENIED") -> None:
        self.code = code
        super().__init__(code)


class SubjectAuthorizer(Protocol):
    """Must use a trusted, server-side identity + tenant-membership authority."""

    def may_submit(self, authenticated_user_id: UUID, tenant_id: str) -> bool: ...


@dataclass(frozen=True, repr=False)
class AuthorizedCvSubmission:
    """Non-loggable, in-memory job ready for a *separately approved* sandbox.

    Do not serialize or log this object. The document remains ephemeral here.
    """

    user_id: UUID
    tenant_id: str
    idempotency_key: str
    filename: str
    filetype: str
    document: bytes
    sha256: str

    def __repr__(self) -> str:
        return "AuthorizedCvSubmission(<REDACTED>)"


def _content_type(filename: str, content: bytes) -> str:
    """Cheap signature check only; never unzip or parse PDFs in the API/gateway."""
    if filename.lower().endswith(".pdf") and content.startswith(b"%PDF-"):
        return "pdf"
    if filename.lower().endswith(".docx") and content.startswith(b"PK\x03\x04"):
        return "docx"
    if filename.lower().endswith(".txt") and b"\x00" not in content:
        try:
            content.decode("utf-8-sig", errors="strict")
            return "txt"
        except UnicodeError:
            pass
    raise CvIntakeRejected("CV_FORMAT")


def authorize_cv_submission(
    job: ValidatedJob,
    *,
    authenticated_user_id: UUID,
    requested_tenant_id: str,
    authorizer: SubjectAuthorizer,
    explicit_processing_consent: bool,
) -> AuthorizedCvSubmission:
    """Fail closed on session/tenant mismatch, lack of consent or unsafe file header.

    A real CV is not passed to a parser until an independently approved broker,
    subject policy and isolated worker are installed. This function does NOT
    assert that such an executor exists.
    """
    if (
        job.operation != "submit"
        or not explicit_processing_consent
        or job.user_id != authenticated_user_id
        or job.tenant_id != requested_tenant_id
        or not authorizer.may_submit(authenticated_user_id, requested_tenant_id)
    ):
        raise CvIntakeRejected()
    content = job.document
    if (
        not content
        or not isinstance(content, bytes)
        or len(content) > MAX_DOCUMENT_BYTES
        or not job.filename
        or not job.idempotency_key
    ):
        raise CvIntakeRejected("CV_SIZE")
    filetype = _content_type(job.filename, content)
    return AuthorizedCvSubmission(
        user_id=authenticated_user_id,
        tenant_id=requested_tenant_id,
        idempotency_key=job.idempotency_key,
        filename=job.filename,
        filetype=filetype,
        document=content,
        sha256=hashlib.sha256(content).hexdigest(),
    )
