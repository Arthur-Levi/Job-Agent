"""D2-E1.5 privacy tests use the guarded disposable CI PostgreSQL fixtures only."""
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.core.config import Settings
from app.main import create_app


def test_public_registration_does_not_disclose_account_existence(
    test_database_url: str, db_session: Session
) -> None:
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url=test_database_url,
        allow_legacy_local_user=False,
        registration_privacy_enabled=True,
    )
    app = create_app(settings)
    app.dependency_overrides[get_session] = lambda: db_session
    email = f"public-private-{uuid4().hex}@example.com"
    data = {"email": email, "name": "Synthetic", "password": "Synthetic-TestOnly-12345!"}
    with TestClient(app) as client:
        created = client.post("/api/v1/auth/register", json=data)
        duplicate = client.post("/api/v1/auth/register", json=data)
        assert created.status_code == duplicate.status_code == 202
        assert created.json() == duplicate.json()
        for response in (created, duplicate):
            assert "email" not in response.text.lower()
            assert "id" not in response.json()
            assert response.headers["cache-control"] == "no-store"
            assert response.headers["x-content-type-options"] == "nosniff"
            assert response.headers["referrer-policy"] == "no-referrer"
        # Auth remains usable after generic registration response.
        logged = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": data["password"]},
        )
        assert logged.status_code == 200
        assert logged.headers["cache-control"] == "no-store"


def test_security_headers_apply_to_errors_without_database(
    test_database_url: str, db_session: Session
) -> None:
    settings = Settings(_env_file=None, app_env="test", database_url=test_database_url)
    app = create_app(settings)
    app.dependency_overrides[get_session] = lambda: db_session
    with TestClient(app) as client:
        invalid = client.post("/api/v1/auth/register", json={"bad": "body"})
        assert invalid.status_code == 422
        assert invalid.headers["cache-control"] == "no-store"
        assert invalid.headers["x-frame-options"] == "DENY"
        assert invalid.headers["pragma"] == "no-cache"
