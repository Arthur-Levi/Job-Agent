"""Browser CORS must allow the import confirmation idempotency header."""

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_resume_confirm_preflight_accepts_idempotency_header() -> None:
    settings = Settings(
        app_env="test",
        database_url="postgresql+psycopg://ci:ci@localhost:5432/disposable_test",
        cors_origins=["http://127.0.0.1:5173"],
    )
    with TestClient(create_app(settings)) as client:
        response = client.options(
            "/api/v1/resume-imports/confirm",
            headers={
                "Origin": "http://127.0.0.1:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type,idempotency-key",
            },
        )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    allowed = response.headers["access-control-allow-headers"].lower()
    assert "idempotency-key" in allowed
    assert "authorization" in allowed
    assert "content-type" in allowed
