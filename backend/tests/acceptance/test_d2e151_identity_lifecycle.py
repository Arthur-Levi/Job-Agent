"""D2-E1.5.1 transactional email lifecycle with an in-memory-only outbox.

Guarded integration fixtures RESET the public schema of the supplied *_test DB.
Use exclusively disposable CI PostgreSQL; never target Codespaces preserved DBs.
"""
from datetime import timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.core.config import Settings
from app.main import create_app
from app.models import AuthActionToken
from app.services.auth import digest, now_utc
from app.services.email_delivery import MemoryMailer


def lifecycle_client(database_url: str, session: Session) -> TestClient:
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url=database_url,
        registration_privacy_enabled=True,
        identity_lifecycle_enabled=True,
        email_delivery_mode="memory",
        allow_legacy_local_user=False,
    )
    app = create_app(settings)
    app.dependency_overrides[get_session] = lambda: session
    return TestClient(app)


def _last_token(client: TestClient) -> str:
    mailer = client.app.state.mailer
    assert isinstance(mailer, MemoryMailer)
    assert mailer.messages
    link = mailer.messages[-1].link
    assert "#token=" in link
    return link.partition("#token=")[2]


def test_verification_required_single_use_and_replay_denied(
    test_database_url: str, db_session: Session
) -> None:
    with lifecycle_client(test_database_url, db_session) as client:
        email = f"d2e151-verify-{uuid4().hex}@example.com"
        identity = {
            "name": "Synthetic Verification", "email": email,
            "password": "TestOnly-Synthetic-StrongPassword123!",
        }
        first = client.post("/api/v1/auth/register", json=identity)
        assert first.status_code == 202
        login = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": identity["password"]},
        )
        assert login.status_code == 401
        token = _last_token(client)
        record = db_session.get(AuthActionToken, digest(token))
        assert record is not None
        assert token != record.token_hash
        assert client.post("/api/v1/auth/verify-email", json={"token": token}).status_code == 204
        assert client.post("/api/v1/auth/verify-email", json={"token": token}).status_code == 400
        logged = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": identity["password"]},
        )
        assert logged.status_code == 200
        assert logged.json()["access_token"]


def test_reset_revokes_all_sessions_and_invalidates_old_password(
    test_database_url: str, db_session: Session
) -> None:
    with lifecycle_client(test_database_url, db_session) as client:
        email = f"d2e151-reset-{uuid4().hex}@example.com"
        old_password = "TestOnly-OldPassword-12345!"
        new_password = "TestOnly-NewPassword-12345!"
        assert client.post(
            "/api/v1/auth/register",
            json={"name": "Synthetic Reset", "email": email, "password": old_password},
        ).status_code == 202
        verify_token = _last_token(client)
        assert client.post(
            "/api/v1/auth/verify-email", json={"token": verify_token}
        ).status_code == 204
        sessions = []
        for _ in range(2):
            response = client.post(
                "/api/v1/auth/login", json={"email": email, "password": old_password}
            )
            assert response.status_code == 200
            sessions.append(response.json()["access_token"])
        assert client.post(
            "/api/v1/auth/request-password-reset", json={"email": email}
        ).status_code == 202
        reset_token = _last_token(client)
        assert client.post(
            "/api/v1/auth/reset-password",
            json={"token": reset_token, "new_password": new_password},
        ).status_code == 204
        assert client.post(
            "/api/v1/auth/reset-password",
            json={"token": reset_token, "new_password": new_password},
        ).status_code == 400
        for bearer in sessions:
            assert client.get(
                "/api/v1/auth/me", headers={"Authorization": f"Bearer {bearer}"}
            ).status_code == 401
        assert client.post(
            "/api/v1/auth/login", json={"email": email, "password": old_password}
        ).status_code == 401
        assert client.post(
            "/api/v1/auth/login", json={"email": email, "password": new_password}
        ).status_code == 200


def test_expiry_and_unknown_email_do_not_disclose_or_deliver(
    test_database_url: str, db_session: Session
) -> None:
    with lifecycle_client(test_database_url, db_session) as client:
        email = f"d2e151-expiry-{uuid4().hex}@example.com"
        unknown = f"d2e151-unknown-{uuid4().hex}@example.com"
        assert client.post(
            "/api/v1/auth/register",
            json={"name": "Synthetic Expiry", "email": email,
                  "password": "TestOnly-Password-567890!"}
        ).status_code == 202
        raw = _last_token(client)
        mailer = client.app.state.mailer
        assert isinstance(mailer, MemoryMailer)
        sent_before = len(mailer.messages)
        unknown_result = client.post(
            "/api/v1/auth/request-verification", json={"email": unknown}
        )
        known_result = client.post(
            "/api/v1/auth/request-verification", json={"email": email}
        )
        assert unknown_result.status_code == known_result.status_code == 202
        assert unknown_result.json() == known_result.json()
        assert len(mailer.messages) == sent_before + 1
        # New token revokes the older verification token.
        assert client.post("/api/v1/auth/verify-email", json={"token": raw}).status_code == 400
        current = _last_token(client)
        record = db_session.get(AuthActionToken, digest(current))
        assert record is not None
        record.expires_at = now_utc() - timedelta(seconds=1)
        db_session.flush()
        assert client.post(
            "/api/v1/auth/verify-email", json={"token": current}
        ).status_code == 400
        # No outbox messages should be generated for nonexistent reset identities.
        count = len(mailer.messages)
        assert client.post(
            "/api/v1/auth/request-password-reset", json={"email": unknown}
        ).status_code == 202
        assert len(mailer.messages) == count
