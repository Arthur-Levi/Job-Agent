from collections.abc import Iterator
from typing import Any, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.core.config import Settings
from app.core.errors import ConflictError
from app.main import create_app

# Engine é preguiçoso: esta URL nunca é conectada nos testes unitários/API.
DUMMY_DATABASE_URL = "postgresql+psycopg://test_user:test_pass@localhost:5432/job_agent_test"


class FakeSession:
    """Dublê mínimo de Session para testar rotas sem banco."""

    def __init__(self, error: Exception | None = None) -> None:
        self._error = error

    def execute(self, *_: Any, **__: Any) -> None:
        if self._error is not None:
            raise self._error


class EchoPayload(BaseModel):
    name: str


def _echo(payload: EchoPayload) -> EchoPayload:
    return payload


def _boom() -> None:
    raise RuntimeError("super secret internal detail")


def _app_error() -> None:
    raise ConflictError("Already exists", code="THING_EXISTS", details={"field": "name"})


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        database_url=DUMMY_DATABASE_URL,
        log_level="WARNING",
        cors_origins=["http://localhost:5173"],
        max_request_bytes=1024,
    )


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    application = create_app(settings)
    # Rotas exclusivas de teste, para exercitar handlers sem depender de rotas de negócio.
    application.add_api_route("/__test/echo", _echo, methods=["POST"])
    application.add_api_route("/__test/boom", _boom, methods=["GET"])
    application.add_api_route("/__test/app-error", _app_error, methods=["GET"])
    application.dependency_overrides[get_session] = lambda: cast(Session, FakeSession())
    return application


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def client_no_raise(app: FastAPI) -> Iterator[TestClient]:
    """Devolve 500 como resposta em vez de re-levantar a exceção no teste."""
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
