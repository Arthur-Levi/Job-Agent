import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.support import safe_test_database_url


def _settings(url: str, connect_timeout: int = 5) -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        database_url=url,
        log_level="WARNING",
        db_connect_timeout_seconds=connect_timeout,
    )


def test_ready_returns_503_when_database_is_unreachable() -> None:
    # Porta 1 recusa conexão imediatamente: exercita o caminho real de falha, sem mocks.
    settings = _settings("postgresql+psycopg://u:p@127.0.0.1:1/x", connect_timeout=1)
    with TestClient(create_app(settings)) as client:
        response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DATABASE_UNAVAILABLE"


def test_ready_when_database_available() -> None:
    url = safe_test_database_url()
    if url is None:
        pytest.skip("TEST_DATABASE_URL não definida")
    with TestClient(create_app(_settings(url))) as client:
        response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["checks"] == {"database": "ok"}
