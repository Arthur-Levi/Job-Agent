from typing import cast

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.api.deps import get_session
from tests.conftest import FakeSession


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_returns_ready_when_database_responds(client: TestClient) -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "checks": {"database": "ok"}}


def test_ready_returns_503_when_database_fails(app: FastAPI, client: TestClient) -> None:
    failing = FakeSession(OperationalError("SELECT 1", {}, Exception("password=hunter2")))
    app.dependency_overrides[get_session] = lambda: cast(Session, failing)

    response = client.get("/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "DATABASE_UNAVAILABLE"
    assert "hunter2" not in response.text
