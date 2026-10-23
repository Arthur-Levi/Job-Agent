"""Estratégia de isolamento do banco de teste.

1. TEST_DATABASE_URL é obrigatória e o NOME do banco deve terminar em "_test"
   (tests.support.safe_test_database_url). Nunca se usa DATABASE_URL aqui.
2. Início da sessão: o schema `public` do banco de teste é recriado e as MIGRATIONS
   rodam até `head`. O schema dos testes é, portanto, exatamente o das migrations.
3. Cada teste roda numa transação externa com SAVEPOINT e faz ROLLBACK no fim:
   `session.commit()` dentro de um service não persiste nada entre testes.
4. REQUIRE_TEST_DATABASE=1 (CI) transforma "sem banco" em FALHA, não em skip.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.core.config import Settings
from app.main import create_app
from tests.support import safe_test_database_url

BACKEND_DIR = Path(__file__).resolve().parents[2]


def migrate(engine: Engine, action: str, revision: str) -> None:
    """Roda `alembic upgrade|downgrade <revision>` na conexão do engine de teste."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        if action == "upgrade":
            command.upgrade(config, revision)
        else:
            command.downgrade(config, revision)


def reset_schema(engine: Engine) -> None:
    with engine.begin() as connection:
        database = str(connection.execute(text("SELECT current_database()")).scalar_one())
        if not database.endswith("_test"):  # defesa em profundidade, na própria conexão
            raise RuntimeError(f"refusing to reset non-test database {database!r}")
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))


@pytest.fixture(scope="session")
def test_database_url() -> str:
    url = safe_test_database_url()
    if url is None:
        if os.environ.get("REQUIRE_TEST_DATABASE") == "1":
            pytest.fail("TEST_DATABASE_URL is required (REQUIRE_TEST_DATABASE=1)")
        pytest.skip("TEST_DATABASE_URL não definida")
    return url


@pytest.fixture(scope="session")
def migrated_engine(test_database_url: str) -> Iterator[Engine]:
    engine = create_engine(test_database_url)
    reset_schema(engine)
    migrate(engine, "upgrade", "head")
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(migrated_engine: Engine) -> Iterator[Session]:
    connection = migrated_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def api_client(test_database_url: str, db_session: Session) -> Iterator[TestClient]:
    """App real (todas as camadas) sobre o banco de teste, na transação do teste.

    `session.commit()` dos services só libera o SAVEPOINT; o rollback final descarta tudo.
    """
    settings = Settings(
        _env_file=None, app_env="test", database_url=test_database_url, log_level="WARNING"
    )
    app = create_app(settings)
    app.dependency_overrides[get_session] = lambda: db_session
    with TestClient(app) as client:
        yield client
