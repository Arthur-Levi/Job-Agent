from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.devtools.seed import seed_development_data


def dev_settings(database_url: str) -> Settings:
    return Settings(_env_file=None, app_env="development", database_url=database_url)


def count(session: Session, table: str) -> int:
    return int(session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())


def test_seed_creates_the_documented_dataset(db_session: Session, test_database_url: str) -> None:
    report = seed_development_data(db_session, dev_settings(test_database_url))

    assert report.skipped == []
    assert [
        count(db_session, t) for t in ("users", "candidate_profiles", "jobs", "applications")
    ] == [
        1,
        1,
        2,
        1,
    ]
    events = db_session.execute(
        text("SELECT event_type, to_status FROM application_events ORDER BY created_at, id")
    ).all()
    assert [tuple(row) for row in events] == [
        ("CREATED", "DISCOVERED"),
        ("STATUS_CHANGED", "QUALIFIED"),
    ]


def test_seed_is_idempotent(db_session: Session, test_database_url: str) -> None:
    settings = dev_settings(test_database_url)
    seed_development_data(db_session, settings)
    again = seed_development_data(db_session, settings)

    assert again.created == []
    assert len(again.skipped) == 5  # user, profile, 2 jobs, application
    assert [
        count(db_session, t) for t in ("users", "jobs", "applications", "application_events")
    ] == [
        1,
        2,
        1,
        2,
    ]


def test_seeded_data_is_visible_through_the_api(
    api_client: TestClient, db_session: Session, test_database_url: str
) -> None:
    """O seed pertence ao usuário padrão: é o mesmo que o frontend usa."""
    seed_development_data(db_session, dev_settings(test_database_url))

    assert api_client.get("/api/v1/jobs").json()["total"] == 2
    assert api_client.get("/api/v1/applications").json()["total"] == 1
    assert api_client.get("/api/v1/profile").status_code == 200
    application = api_client.get("/api/v1/applications").json()["items"][0]
    assert application["status"] == "QUALIFIED"
    assert application["job"]["company"] == "Example Corp"
