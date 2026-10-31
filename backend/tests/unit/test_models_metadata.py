"""Guardas estruturais sobre o schema, sem banco: rodam sempre, inclusive em CI sem Postgres."""

from sqlalchemy import DateTime, UniqueConstraint, Uuid

import app.models  # noqa: F401
from app.db.base import Base
from app.domain.enums import ApplicationStatus

EXPECTED_TABLES = {
    "users",
    "auth_credentials",
    "auth_sessions",
    "auth_rate_limits",
    "auth_action_tokens",
    "candidate_profiles",
    "candidate_skills",
    "candidate_projects",
    "candidate_experiences",
    "candidate_educations",
    "jobs",
    "job_requirements",
    "job_matches",
    "resume_versions",
    "applications",
    "application_events",
}
USER_OWNED = {
    "candidate_profiles",
    "jobs",
    "resume_versions",
    "applications",
    "auth_credentials",
    "auth_sessions",
}


def test_expected_tables_exist() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_every_primary_key_is_a_uuid() -> None:
    for table in Base.metadata.tables.values():
        if table.name in {"auth_rate_limits", "auth_action_tokens"}:
            expected = ["key_digest" if table.name == "auth_rate_limits" else "token_hash"]
        else:
            expected = ["user_id"] if table.name == "auth_credentials" else ["id"]
        assert [c.name for c in table.primary_key.columns] == expected, table.name
        pk = next(iter(table.primary_key.columns))
        if table.name not in {"auth_rate_limits", "auth_action_tokens"}:
            assert isinstance(pk.type, Uuid), table.name


def test_user_owned_tables_have_user_id() -> None:
    for name in USER_OWNED:
        assert "user_id" in Base.metadata.tables[name].c, name


def test_every_datetime_column_is_timezone_aware() -> None:
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, DateTime):
                assert column.type.timezone, f"{table.name}.{column.name}"


def test_every_foreign_key_declares_a_deliberate_ondelete() -> None:
    for table in Base.metadata.tables.values():
        for fk in table.foreign_key_constraints:
            assert fk.ondelete in {"CASCADE", "RESTRICT", "SET NULL"}, f"{table.name}: {fk.name}"


def test_every_foreign_key_is_covered_by_an_index() -> None:
    """O PostgreSQL não indexa FKs sozinho; sem índice, DELETE no pai varre a tabela filha."""
    for table in Base.metadata.tables.values():
        indexed_prefixes: list[list[str]] = [list(idx.columns.keys()) for idx in table.indexes]
        indexed_prefixes += [
            list(c.columns.keys()) for c in table.constraints if isinstance(c, UniqueConstraint)
        ]
        # PostgreSQL indexes the primary key automatically; auth_credentials uses
        # user_id as a UUID primary key and foreign key simultaneously.
        indexed_prefixes.append([c.name for c in table.primary_key.columns])
        for fk in table.foreign_key_constraints:
            cols = [c.name for c in fk.columns]
            assert any(p[: len(cols)] == cols for p in indexed_prefixes), f"{table.name}: {cols}"


def test_application_status_matches_the_spec() -> None:
    assert [s.value for s in ApplicationStatus] == [
        "DISCOVERED",
        "QUALIFIED",
        "PREPARED",
        "READY",
        "APPLIED",
        "RESPONSE",
        "INTERVIEW",
        "TECHNICAL",
        "OFFER",
        "REJECTED",
        "WITHDRAWN",
        "GHOSTED",
    ]
