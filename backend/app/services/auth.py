"""Security service for D2-E1 (explicit auth only).

Opaque bearer tokens are returned once, never persisted in plaintext.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import AuthCredential, AuthSession, User
from app.repositories.user import UserRepository

PASSWORD_HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
SESSION_TTL = timedelta(hours=12)
# Always verify one Argon2 hash to reduce timing differences for unknown accounts.
_DUMMY_PASSWORD_HASH = PASSWORD_HASHER.hash(secrets.token_urlsafe(32))


class DuplicateAccount(Exception):
    pass


class InvalidCredentials(Exception):
    pass


def now_utc() -> datetime:
    return datetime.now(UTC)


def digest(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def register(session: Session, *, name: str, email: str, password: str) -> User:
    # DB's unique lower(email) index remains authoritative under races.
    email = email.strip().lower()
    if UserRepository(session).get_by_email(email):
        raise DuplicateAccount
    try:
        user = User(name=name.strip(), email=email)
        session.add(user)
        session.flush()
        session.add(AuthCredential(user_id=user.id, password_hash=PASSWORD_HASHER.hash(password)))
        session.commit()
        return user
    except IntegrityError as exc:
        session.rollback()
        raise DuplicateAccount from exc
    except BaseException:
        session.rollback()
        raise


def login(
    session: Session, *, email: str, password: str, require_verified: bool = False
) -> str:
    user = UserRepository(session).get_by_email(email.strip())
    credential = session.get(AuthCredential, user.id) if user else None
    candidate_hash = credential.password_hash if credential else _DUMMY_PASSWORD_HASH
    verified = False
    try:
        PASSWORD_HASHER.verify(candidate_hash, password)
        verified = True
    except (VerificationError, ValueError):
        pass
    if credential is None or user is None or not verified:
        raise InvalidCredentials
    if require_verified and user.email_verified_at is None:
        raise InvalidCredentials
    token = secrets.token_urlsafe(48)
    session.add(
        AuthSession(
            user_id=user.id,
            token_hash=digest(token),
            expires_at=now_utc() + SESSION_TTL,
        )
    )
    session.commit()
    return token


def current(session: Session, token: str) -> User | None:
    if len(token) < 32 or len(token) > 256 or not token.isascii():
        return None
    record = session.execute(
        select(AuthSession).where(AuthSession.token_hash == digest(token))
    ).scalar_one_or_none()
    if not record or record.revoked_at is not None:
        return None
    expiry = record.expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=UTC)
    if expiry <= now_utc():
        return None
    return session.get(User, record.user_id)


def logout(session: Session, token: str) -> None:
    if not (32 <= len(token) <= 256 and token.isascii()):
        return
    record = session.execute(
        select(AuthSession).where(AuthSession.token_hash == digest(token))
    ).scalar_one_or_none()
    if record and record.revoked_at is None:
        record.revoked_at = now_utc()
        session.commit()
