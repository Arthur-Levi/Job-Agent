from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection

import app.models  # noqa: F401  (registra todos os models em Base.metadata)
from app.core.config import Settings
from app.core.logging import configure_logging
from app.db.base import Base

config = context.config
target_metadata = Base.metadata


def _configure_and_run(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_offline() -> None:
    url = Settings().database_url.get_secret_value()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Os testes injetam a própria conexão (banco de teste); a CLI usa Settings/DATABASE_URL.
    injected: Connection | None = config.attributes.get("connection")
    if injected is not None:
        _configure_and_run(injected)
        return

    settings = Settings()
    configure_logging(settings.log_level)
    engine = create_engine(settings.database_url.get_secret_value(), poolclass=pool.NullPool)
    try:
        with engine.connect() as connection:
            _configure_and_run(connection)
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
