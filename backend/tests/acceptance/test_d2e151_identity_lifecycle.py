"""D2-E1.5.1 lifecycle acceptance — destructive fixtures require disposable *_test DB."""

from datetime import timedelta
from typing import cast
from uuid import uuid4

from fastapi import FastAPI
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


def mailer_for(client: TestClient) -> MemoryMailer:
    mailer = cast(FastAPI, client.app).state.mailer
    assert isinstance(mailer, MemoryMailer)
    return mailer


def last_token(client: TestClient) -> str:
    messages = mailer_for(client).messages
    assert messages
    link = messages[-1].link
    assert "#token=" in link
    return link.partition("#token=")[2]


def post_status(client: TestClient, route: str, payload: dict[str, str]) -> int:
    return int(client.post("/api/v1/auth/" + route, json=payload).status_code)


def test_verification_required_single_use_and_replay_denied(
    test_database_url: str, db_session: Session
) -> None:
    with lifecycle_client(test_database_url, db_session) as client:
        email = f"d2e151-verify-{uuid4().hex}@example.com"
        password = "TestOnly-Synthetic-StrongPassword123!"
        registered = post_status(
            client, "register", {"name": "Synthetic", "email": email, "password": password}
        )
        assert registered == 202
        assert post_status(client, "login", {"email": email, "password": password}) == 401
        raw = last_token(client)
        record = db_session.get(AuthActionToken, digest(raw))
        assert record is not None
        assert raw != record.token_hash
        assert post_status(client, "verify-email", {"token": raw}) == 204
        assert post_status(client, "verify-email", {"token": raw}) == 400
        assert post_status(client, "login", {"email": email, "password": password}) == 200


def test_reset_revokes_all_sessions_and_old_password(
    test_database_url: str, db_session: Session
) -> None:
    with lifecycle_client(test_database_url, db_session) as client:
        email = f"d2e151-reset-{uuid4().hex}@example.com"
        old = "TestOnly-OldPassword-12345!"
        new = "TestOnly-NewPassword-12345!"
        registration_payload = {"name": "Synthetic", "email": email, "password": old}
        registered = post_status(client, "register", registration_payload)
        assert registered == 202
        assert post_status(client, "verify-email", {"token": last_token(client)}) == 204
        sessions: list[str] = []
        for _ in range(2):
            response = client.post("/api/v1/auth/login", json={"email": email, "password": old})
            assert response.status_code == 200
            sessions.append(str(response.json()["access_token"]))
        assert post_status(client, "request-password-reset", {"email": email}) == 202
        raw = last_token(client)
        assert post_status(client, "reset-password", {"token": raw, "new_password": new}) == 204
        assert post_status(client, "reset-password", {"token": raw, "new_password": new}) == 400
        for bearer in sessions:
            response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {bearer}"})
            assert response.status_code == 401
        assert post_status(client, "login", {"email": email, "password": old}) == 401
        assert post_status(client, "login", {"email": email, "password": new}) == 200


def test_expiry_and_unknown_email_do_not_disclose(
    test_database_url: str, db_session: Session
) -> None:
    with lifecycle_client(test_database_url, db_session) as client:
        email = f"d2e151-expiry-{uuid4().hex}@example.com"
        unknown = f"d2e151-unknown-{uuid4().hex}@example.com"
        registered = post_status(
            client,
            "register",
            {"name": "Synthetic", "email": email, "password": "TestOnly-Password-567890!"},
        )
        assert registered == 202
        old = last_token(client)
        count = len(mailer_for(client).messages)
        unknown_response = client.post("/api/v1/auth/request-verification", json={"email": unknown})
        known_response = client.post("/api/v1/auth/request-verification", json={"email": email})
        assert unknown_response.status_code == known_response.status_code == 202
        assert unknown_response.json() == known_response.json()
        assert len(mailer_for(client).messages) == count + 1
        assert post_status(client, "verify-email", {"token": old}) == 400
        current = last_token(client)
        record = db_session.get(AuthActionToken, digest(current))
        assert record is not None
        record.expires_at = now_utc() - timedelta(seconds=1)
        db_session.flush()
        assert post_status(client, "verify-email", {"token": current}) == 400
        count = len(mailer_for(client).messages)
        assert post_status(client, "request-password-reset", {"email": unknown}) == 202
        assert len(mailer_for(client).messages) == count
