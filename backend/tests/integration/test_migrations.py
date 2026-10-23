import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Engine, inspect, text

from app.db.base import Base
from tests.integration.conftest import migrate

pytestmark = pytest.mark.usefixtures("migrated_engine")


def _tables(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names()) - {"alembic_version"}


def test_upgrade_head_creates_every_model_table(migrated_engine: Engine) -> None:
    assert _tables(migrated_engine) == set(Base.metadata.tables)


def test_models_and_migrations_are_in_sync(migrated_engine: Engine) -> None:
    """Se um model mudar sem migration nova, este teste falha (drift)."""
    with migrated_engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_type": True})
        assert compare_metadata(context, Base.metadata) == []


def test_application_events_trigger_is_installed(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        names = connection.execute(text("SELECT tgname FROM pg_trigger WHERE NOT tgisinternal"))
        assert [row[0] for row in names] == ["trg_application_events_append_only"]


def test_downgrade_to_base_then_upgrade_again(migrated_engine: Engine) -> None:
    try:
        migrate(migrated_engine, "downgrade", "base")
        assert _tables(migrated_engine) == set()
        with migrated_engine.connect() as connection:
            functions = connection.execute(
                text("SELECT proname FROM pg_proc WHERE proname LIKE 'prevent_application_event%'")
            ).all()
        assert functions == []
    finally:
        migrate(migrated_engine, "upgrade", "head")  # nunca deixa o banco de teste em "base"
    assert _tables(migrated_engine) == set(Base.metadata.tables)
