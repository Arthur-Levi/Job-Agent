"""API-to-gateway authentication tests; synthetic bytes and mock auth lookup only."""

import base64
import json
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from app.models.user import User
from app.services import auth
from app.workers.cv_real_intake import CvIntakeRejected
from app.workers.secops_api_submission import prepare_authenticated_submission
from app.workers.secops_authenticated_chain import _decode_frame

SECRET = b"f123-api-service-key-" + b"x" * 32


class Membership:
    def __init__(self, allowed: bool = True) -> None:
        self.allowed = allowed

    def may_submit(self, authenticated_user_id: UUID, tenant_id: str) -> bool:
        return self.allowed and tenant_id == "tenant-test"


def job_raw(user_id: UUID, *, tenant: str = "tenant-test") -> bytes:
    return json.dumps(
        {
            "version": 1,
            "operation": "submit",
            "request_id": str(uuid4()),
            "idempotency_key": "synthetic-idempotency",
            "subject": {"user_id": str(user_id), "tenant_id": tenant},
            "payload": {
                "filename": "synthetic.txt",
                "content_b64": base64.b64encode(b"synthetic CV only").decode("ascii"),
            },
        }
    ).encode()


def test_signed_api_frame_is_derived_from_authenticated_backend_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User(name="synthetic", email=None)
    user.id = uuid4()
    monkeypatch.setattr(auth, "current", lambda session, token: user if token == "valid" else None)
    raw = job_raw(user.id)
    prepared = prepare_authenticated_submission(
        cast(Session, object()),
        bearer_token="valid",
        raw_job_envelope=raw,
        requested_tenant_id="tenant-test",
        membership=Membership(),
        explicit_processing_consent=True,
        api_service_id="api-test",
        api_secret=SECRET,
    )
    payload, service, timestamp, nonce, signature = _decode_frame(prepared.signed_frame)
    assert payload == raw
    assert service == "api-test"
    assert timestamp > 0 and len(nonce) >= 16 and len(signature) == 64
    assert prepared.user_id == user.id
    assert repr(prepared) == "PreparedAuthenticatedSubmission(<REDACTED>)"


@pytest.mark.parametrize(
    "case",
    ["revoked", "wrong_user", "wrong_tenant", "no_consent", "no_member"],
)
def test_no_signature_issued_for_unauthorized_cv(
    monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    user = User(name="synthetic", email=None)
    user.id = uuid4()
    monkeypatch.setattr(auth, "current", lambda session, token: None if case == "revoked" else user)
    raw = job_raw(uuid4() if case == "wrong_user" else user.id)
    with pytest.raises(CvIntakeRejected, match="CV_INTAKE_DENIED"):
        prepare_authenticated_submission(
            cast(Session, object()),
            bearer_token="invalid" if case == "revoked" else "valid",
            raw_job_envelope=raw,
            requested_tenant_id="another-tenant" if case == "wrong_tenant" else "tenant-test",
            membership=Membership(allowed=case != "no_member"),
            explicit_processing_consent=case != "no_consent",
            api_service_id="api-test",
            api_secret=SECRET,
        )


def test_backend_identity_query_failure_is_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(session: Session, token: str) -> None:
        raise RuntimeError("sensitive database failure")

    monkeypatch.setattr(auth, "current", broken)
    with pytest.raises(CvIntakeRejected, match="CV_INTAKE_DENIED") as exc:
        prepare_authenticated_submission(
            cast(Session, object()),
            bearer_token="some bearer",
            raw_job_envelope=job_raw(uuid4()),
            requested_tenant_id="tenant-test",
            membership=Membership(),
            explicit_processing_consent=True,
            api_service_id="api-test",
            api_secret=SECRET,
        )
    assert "sensitive" not in str(exc.value)
