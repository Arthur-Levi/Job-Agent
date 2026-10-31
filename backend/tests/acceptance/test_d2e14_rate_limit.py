"""D2-E1.4 abuse controls — opt-in PostgreSQL acceptance only.

These tests use the existing disposable *_test integration fixture.
Never run against an original, shared, or production DB: the fixture resets schema.
"""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.core.config import Settings
from app.main import create_app


def _client(
    database_url: str, session: Session, *, secret: str | None = None, **limits: int
) -> TestClient:
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url=database_url,
        log_level="WARNING",
        allow_legacy_local_user=False,
        auth_rate_limit_enabled=True,
        auth_rate_limit_secret=secret or ("D2E1-TEST-ONLY-" + uuid4().hex + uuid4().hex),
        **limits,
    )
    app = create_app(settings)
    app.dependency_overrides[get_session] = lambda: session
    return TestClient(app)


def test_d2e14_registration_ip_throttle_includes_bad_payloads(
    test_database_url: str, db_session: Session
) -> None:
    with _client(test_database_url, db_session, auth_register_ip_max=2) as client:
        path = "/api/v1/auth/register"
        # Validation errors consume IP capacity too; fake forwarded header is ignored.
        for i in range(2):
            response = client.post(
                path,
                json={"invalid": i},
                headers={"X-Forwarded-For": f"203.0.113.{i + 1}"},
            )
            assert response.status_code == 422
        blocked = client.post(path, json={"invalid": 3})
        assert blocked.status_code == 429
        assert int(blocked.headers["Retry-After"]) > 0
        assert blocked.json()["error"]["code"] == "RATE_LIMITED"


def test_d2e14_account_throttle_and_generic_bad_login(
    test_database_url: str, db_session: Session
) -> None:
    with _client(
        test_database_url,
        db_session,
        auth_login_ip_max=20,
        auth_login_account_max=2,
    ) as client:
        path = "/api/v1/auth/login"
        email = f"synthetic-{uuid4().hex}@example.com"
        for _ in range(2):
            wrong = client.post(path, json={"email": email, "password": "bad-pass"})
            assert wrong.status_code == 401
            assert wrong.json()["error"]["message"] == "Credenciais inválidas"
        blocked = client.post(path, json={"email": email.upper(), "password": "bad-pass"})
        assert blocked.status_code == 429
        assert int(blocked.headers["Retry-After"]) > 0
        other = client.post(
            path, json={"email": f"other-{uuid4().hex}@example.com", "password": "bad-pass"}
        )
        assert other.status_code == 401


def test_d2e14_register_returns_503_when_counter_store_is_unavailable(
    test_database_url: str, db_session: Session, monkeypatch
) -> None:
    from app.core import middleware
    from app.services.auth_rate_limit import RateLimitUnavailable

    with _client(test_database_url, db_session) as client:

        def unavailable(*args, **kwargs):
            raise RateLimitUnavailable

        monkeypatch.setattr(middleware, "consume", unavailable)
        response = client.post("/api/v1/auth/register", json={"invalid": True})
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "AUTH_PROTECTION_UNAVAILABLE"


def test_d2e14_shared_counters_survive_multiple_app_instances(
    test_database_url: str, db_session: Session
) -> None:
    # Two independent FastAPI instances with separate engine pools but common HMAC key.
    shared_key = "D2E1-TEST-SHARED-" + uuid4().hex + uuid4().hex
    options = {"auth_register_ip_max": 2}
    with (
        _client(test_database_url, db_session, secret=shared_key, **options) as first,
        _client(test_database_url, db_session, secret=shared_key, **options) as second,
    ):
        path = "/api/v1/auth/register"
        assert first.post(path, json={"invalid": 1}).status_code == 422
        assert second.post(path, json={"invalid": 2}).status_code == 422
        blocked = first.post(path, json={"invalid": 3})
        assert blocked.status_code == 429
        assert blocked.json()["error"]["code"] == "RATE_LIMITED"
