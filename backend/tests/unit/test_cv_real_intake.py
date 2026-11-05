"""Real-CV intake policy uses fake documents only; no real upload or parser."""

import base64
import json
from dataclasses import FrozenInstanceError
from uuid import UUID, uuid4

import pytest

from app.workers.cv_real_intake import (
    AuthorizedCvSubmission,
    CvIntakeRejected,
    authorize_cv_submission,
)
from app.workers.job_protocol import ValidatedJob, validate_job_envelope


class AllowMembership:
    def may_submit(self, authenticated_user_id: UUID, tenant_id: str) -> bool:
        return tenant_id == "tenant-a" and authenticated_user_id.int != 0


class DenyMembership:
    def may_submit(self, authenticated_user_id: UUID, tenant_id: str) -> bool:
        return False


def synthetic_job(filename: str, data: bytes) -> tuple[ValidatedJob, UUID]:
    user_id = uuid4()
    raw = json.dumps(
        {
            "version": 1,
            "operation": "submit",
            "request_id": str(uuid4()),
            "idempotency_key": "synthetic-idempotency",
            "subject": {"user_id": str(user_id), "tenant_id": "tenant-a"},
            "payload": {
                "filename": filename,
                "content_b64": base64.b64encode(data).decode("ascii"),
            },
        }
    ).encode()
    return validate_job_envelope(raw), user_id


def authorize(
    job: ValidatedJob,
    user_id: UUID,
    *,
    consent: bool = True,
    tenant: str = "tenant-a",
    membership: bool = True,
) -> AuthorizedCvSubmission:
    return authorize_cv_submission(
        job,
        authenticated_user_id=user_id,
        requested_tenant_id=tenant,
        authorizer=AllowMembership() if membership else DenyMembership(),
        explicit_processing_consent=consent,
    )


@pytest.mark.parametrize(
    ("filename", "data", "expected"),
    [
        ("synthetic.pdf", b"%PDF-1.7\nFAKE ONLY", "pdf"),
        ("synthetic.docx", b"PK\x03\x04FAKE ONLY", "docx"),
        ("synthetic.txt", b"synthetic resume header", "txt"),
    ],
)
def test_approved_subject_and_document_header(
    filename: str, data: bytes, expected: str
) -> None:
    job, user = synthetic_job(filename, data)
    result = authorize(job, user)
    assert result.filetype == expected
    assert result.document == data
    assert repr(result) == "AuthorizedCvSubmission(<REDACTED>)"
    with pytest.raises(FrozenInstanceError):
        setattr(result, "filename", "different.txt")


@pytest.mark.parametrize(
    ("filename", "data"),
    [
        ("spoofed.pdf", b"not a pdf"),
        ("spoofed.docx", b"PKbad archive"),
        ("malformed.txt", b"header\x00hidden"),
        ("invalid.txt", b"\xff\xfe"),
        ("renamed.pdf", b"PK\x03\x04"),
    ],
)
def test_bad_file_magic_rejected(filename: str, data: bytes) -> None:
    job, user = synthetic_job(filename, data)
    with pytest.raises(CvIntakeRejected, match="CV_FORMAT"):
        authorize(job, user)


@pytest.mark.parametrize("denial", ["missing_consent", "wrong_user", "wrong_tenant", "not_member"])
def test_subject_and_consent_denied(denial: str) -> None:
    job, user = synthetic_job("fake.txt", b"synthetic only")
    if denial == "wrong_user":
        user = uuid4()
    with pytest.raises(CvIntakeRejected, match="CV_INTAKE_DENIED"):
        authorize(
            job,
            user,
            consent=denial != "missing_consent",
            tenant="tenant-b" if denial == "wrong_tenant" else "tenant-a",
            membership=denial != "not_member",
        )


def test_no_document_information_in_error() -> None:
    job, user = synthetic_job("secret-person-name.pdf", b"person-secret-content")
    with pytest.raises(CvIntakeRejected) as err:
        authorize(job, user)
    assert "secret" not in str(err.value)


def test_rejects_not_submit() -> None:
    job, user = synthetic_job("synthetic.txt", b"fake")
    from dataclasses import replace

    with pytest.raises(CvIntakeRejected):
        authorize(replace(job, operation="status"), user)
