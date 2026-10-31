"""One-use verification and password-reset tokens with transactionally revoked sessions.

Raw tokens exist only transiently in the test mailer's message link.
"""

import secrets
from datetime import timedelta
from urllib.parse import quote

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import AuthActionToken, AuthCredential, AuthSession, User
from app.repositories.user import UserRepository
from app.services import auth
from app.services.email_delivery import MemoryMailer

VERIFY = "verify"
RESET = "reset"
TTL = {VERIFY: timedelta(hours=1), RESET: timedelta(minutes=20)}


class InvalidActionToken(Exception):
    pass


def _issue(session: Session, user: User, *, purpose: str) -> str:
    # Lock user row so issuance and redemption do not race for the same identity.
    session.execute(select(User.id).where(User.id == user.id).with_for_update()).one()
    now = auth.now_utc()
    session.execute(
        update(AuthActionToken)
        .where(
            AuthActionToken.user_id == user.id,
            AuthActionToken.purpose == purpose,
            AuthActionToken.consumed_at.is_(None),
        )
        .values(consumed_at=now)
    )
    raw = secrets.token_urlsafe(48)
    session.add(
        AuthActionToken(
            token_hash=auth.digest(raw),
            user_id=user.id,
            purpose=purpose,
            expires_at=now + TTL[purpose],
        )
    )
    session.commit()
    return raw


def dispatch(
    session: Session,
    *,
    email: str,
    purpose: str,
    mailer: MemoryMailer,
    frontend_url: str,
) -> None:
    user = UserRepository(session).get_by_email(email.strip())
    if user is None:
        return
    if purpose == VERIFY and user.email_verified_at is not None:
        return
    if purpose == RESET and user.email_verified_at is None:
        return
    if user.email is None:
        return
    raw = _issue(session, user, purpose=purpose)
    route = "verify-email" if purpose == VERIFY else "reset-password"
    link = f"{frontend_url.rstrip('/')}/{route}#token={quote(raw)}"
    subject = "Confirme seu email" if purpose == VERIFY else "Redefina sua senha"
    mailer.send(user.email, subject, link)


def consume(session: Session, *, token: str, purpose: str, new_password: str | None = None) -> None:
    if not (32 <= len(token) <= 256 and token.isascii()):
        raise InvalidActionToken
    token_hash = auth.digest(token)
    # Resolve a user UUID without mutating; row lock below serializes all tokens per user.
    record = session.get(AuthActionToken, token_hash)
    if record is None or record.purpose != purpose:
        raise InvalidActionToken
    session.execute(select(User.id).where(User.id == record.user_id).with_for_update()).one()
    session.refresh(record)
    expires = record.expires_at
    if expires.tzinfo is None:
        from datetime import UTC

        expires = expires.replace(tzinfo=UTC)
    if record.consumed_at is not None or expires <= auth.now_utc():
        raise InvalidActionToken

    now = auth.now_utc()
    if purpose == VERIFY:
        user = session.get(User, record.user_id)
        if user is None:
            raise InvalidActionToken
        user.email_verified_at = now
    elif purpose == RESET:
        if new_password is None or not 12 <= len(new_password) <= 128:
            raise InvalidActionToken
        credential = session.get(AuthCredential, record.user_id)
        if credential is None:
            raise InvalidActionToken
        credential.password_hash = auth.PASSWORD_HASHER.hash(new_password)
        session.execute(
            update(AuthSession)
            .where(AuthSession.user_id == record.user_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )
    else:
        raise InvalidActionToken

    session.execute(
        update(AuthActionToken)
        .where(AuthActionToken.user_id == record.user_id, AuthActionToken.purpose == purpose)
        .values(consumed_at=now)
    )
    session.commit()
