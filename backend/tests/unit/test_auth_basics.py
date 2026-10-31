"""D2-E1 security invariants without PostgreSQL.

Database-backed register/login/tenant tests live in tests/acceptance and must run
only on the verified disposable React PostgreSQL after an Alembic migration.
"""
import secrets

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app
from app.services.auth import PASSWORD_HASHER, digest


DB = "postgresql+psycopg://dummy:dummy@127.0.0.1:1/dummy_test"


def test_default_identity_is_opt_in_and_forbidden_in_production():
    assert (
        Settings(_env_file=None, database_url=DB, app_env="test").allow_legacy_local_user
        is False
    )
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url=DB,
            app_env="production",
            allow_legacy_local_user=True,
        )


def test_opaque_token_is_not_equal_to_stored_digest():
    token = secrets.token_urlsafe(48)
    hashed = digest(token)
    assert len(hashed) == 64
    assert hashed != token
    assert hashed == digest(token)
    assert digest(token) != digest(secrets.token_urlsafe(48))


def test_password_hasher_is_argon2():
    secret = "TestOnly-password-not-from-real-user-123"
    hashed = PASSWORD_HASHER.hash(secret)
    assert hashed.startswith("$argon2")
    assert secret not in hashed
    assert PASSWORD_HASHER.verify(hashed, secret)


def test_auth_routes_are_versioned_and_bearer_header_allowed():
    settings = Settings(
        _env_file=None,
        database_url=DB,
        app_env="test",
        cors_origins=["http://localhost:5173"],
    )
    app = create_app(settings)
    # Exercise public OpenAPI rather than FastAPI internals: newer FastAPI builds
    # retain included routers as _IncludedRouter until routing is resolved.
    with TestClient(app) as client:
        spec_response = client.get("/openapi.json")
        assert spec_response.status_code == 200
        paths = spec_response.json()["paths"]
        assert {
            "/api/v1/auth/register": "post",
            "/api/v1/auth/login": "post",
            "/api/v1/auth/me": "get",
            "/api/v1/auth/logout": "post",
        }.items() <= {
            path: method
            for path, operations in paths.items()
            for method in operations
        }.items()
        response = client.options(
            "/api/v1/profile",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization",
            },
        )
    assert response.status_code == 200
    assert "authorization" in response.headers["access-control-allow-headers"].lower()
