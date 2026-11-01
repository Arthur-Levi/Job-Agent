"""Opt-in to the verified disposable PostgreSQL integration fixtures for E1 tests.

The shared integration fixtures RESET the public schema. NEVER pass a shared,
original, production, or SEC05 PostgreSQL database as TEST_DATABASE_URL.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.core.config import Settings
from app.main import create_app

# Import explicitly because tests/acceptance is a sibling of tests/integration.
from tests.integration.conftest import db_session, migrated_engine, test_database_url  # noqa: F401


@pytest.fixture
def auth_client(test_database_url: str, db_session: Session) -> Iterator[TestClient]:  # noqa: F811
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url=test_database_url,
        log_level="WARNING",
        allow_legacy_local_user=False,
    )
    app = create_app(settings)
    app.dependency_overrides[get_session] = lambda: db_session
    with TestClient(app) as client:
        yield client
