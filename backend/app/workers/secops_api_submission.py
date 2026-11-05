"""F.1.2.3 API-side authenticated submission adapter (not exposed as an endpoint).

Resolve the bearer with the existing revocable AuthSession-backed identity
service. Never use the legacy local-user fallback for a CV. Tenant authority
MUST query trusted server-side membership; no tenant membership DB exists yet.
The adapter only signs the first hop; it does not invoke a parser or Docker.
"""

import secrets
import time
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.services import auth
from app.workers.cv_real_intake import (
    CvIntakeRejected,
    SubjectAuthorizer,
    authorize_cv_submission,
)
from app.workers.job_protocol import ProtocolValidationError, validate_job_envelope
from app.workers.secops_authenticated_chain import encode_api_message


@dataclass(frozen=True, repr=False)
class PreparedAuthenticatedSubmission:
    """Ephemeral signed frame; avoid logging because it contains document bytes."""

    user_id: UUID
    tenant_id: str
    signed_frame: bytes

    def __repr__(self) -> str:
        return "PreparedAuthenticatedSubmission(<REDACTED>)"


def prepare_authenticated_submission(
    session: Session,
    *,
    bearer_token: str,
    raw_job_envelope: bytes,
    requested_tenant_id: str,
    membership: SubjectAuthorizer,
    explicit_processing_consent: bool,
    api_service_id: str,
    api_secret: bytes,
) -> PreparedAuthenticatedSubmission:
    """Enforce *real backend bearer authentication* before signing API->gateway.

    A further deployment gate is still required: server-side trusted membership
    and actual three-process integration are not yet enabled in public routes.
    """
    try:
        user = auth.current(session, bearer_token)
    except Exception:
        # DB outage or revocation query failure must not become authorization.
        raise CvIntakeRejected() from None
    if user is None:
        raise CvIntakeRejected()
    try:
        job = validate_job_envelope(raw_job_envelope)
    except ProtocolValidationError:
        raise CvIntakeRejected() from None
    accepted = authorize_cv_submission(
        job,
        authenticated_user_id=user.id,
        requested_tenant_id=requested_tenant_id,
        authorizer=membership,
        explicit_processing_consent=explicit_processing_consent,
    )
    signed = encode_api_message(
        raw_job_envelope,
        api_service_id=api_service_id,
        api_secret=api_secret,
        timestamp=int(time.time()),
        nonce=secrets.token_hex(16),
    )
    return PreparedAuthenticatedSubmission(accepted.user_id, accepted.tenant_id, signed)
