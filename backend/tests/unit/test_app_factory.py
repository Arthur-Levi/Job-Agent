import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

URL = "postgresql+psycopg://u:p@localhost/x_test"


def client_for(env: str) -> TestClient:
    settings = Settings(_env_file=None, app_env=env, database_url=URL, log_level="WARNING")
    return TestClient(create_app(settings))


@pytest.mark.parametrize("path", ["/docs", "/openapi.json"])
def test_api_docs_are_disabled_in_production(path: str) -> None:
    with client_for("production") as client:
        assert client.get(path).status_code == 404


@pytest.mark.parametrize("path", ["/docs", "/openapi.json"])
def test_api_docs_are_available_in_development(path: str) -> None:
    with client_for("development") as client:
        assert client.get(path).status_code == 200
