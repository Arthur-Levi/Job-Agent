"""D2-E2.E synthetic PostgreSQL acceptance, disposable CI database only."""

import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.models import CareerFact, User
from app.services.career_diagnostic import career_diagnostic


def _user(db: Session) -> User:
    user = User(name="Synthetic Diagnostic", email=f"diagnostic-{uuid.uuid4()}@example.invalid")
    db.add(user)
    db.flush()
    return user


def _fact(
    db: Session, user: User, *, title: str, category: str, status: str = "ACTIVE", value: str = "{}"
) -> CareerFact:
    fact = CareerFact(
        user_id=user.id,
        import_id=None,
        subject=title,
        predicate=category,
        value=value,
        source_type="user_statement",
        source_reference="synthetic-diagnostic",
        verification="USER_DECLARED",
        status=status,
    )
    db.add(fact)
    db.flush()
    return fact


def test_diagnostic_empty_and_cross_account_isolation(db_session: Session) -> None:
    a = _user(db_session)
    b = _user(db_session)
    _fact(db_session, b, title="Excel", category="skill")
    result = career_diagnostic(db_session, a.id)
    assert result["basis"] == "active_fact_ledger"
    assert result["total_active_facts"] == 0
    assert all(entry["state"] == "not_documented" for entry in result["coverage"])
    assert not any("Excel" in str(entry) for entry in result["coverage"])
    assert len(result["review_actions"]) == 4


def test_diagnostic_cites_only_active_facts_and_reviewable_fields(
    db_session: Session, api_client: TestClient
) -> None:
    user = _user(db_session)
    active = _fact(
        db_session,
        user,
        title="Analista de Dados",
        category="experience",
        value='{"title":"Analista de Dados","organization":null,'
        '"start_date":null,"end_date":"2024","description":"Teste"}',
    )
    superseded = _fact(
        db_session, user, title="Antigo emprego", category="experience", status="SUPERSEDED"
    )
    skill = _fact(db_session, user, title="Excel", category="skill")
    app = api_client.app
    assert isinstance(app, FastAPI)
    app.dependency_overrides[get_current_user] = lambda: user

    response = api_client.get("/api/v1/career/diagnostic")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "preliminary"
    assert data["total_active_facts"] == 2
    assert data["coverage"][0]["state"] == "documented"
    assert data["coverage"][0]["evidence"] == [
        {
            "fact_id": str(active.id),
            "title": active.subject,
            "verification": "USER_DECLARED",
        }
    ]
    assert data["coverage"][3]["evidence"][0]["fact_id"] == str(skill.id)
    assert str(superseded.id) not in str(data)
    assert "Antigo emprego" not in str(data)
    assert any(
        action.get("fact_id") == str(active.id)
        and action["fields"] == ["organization", "start_date"]
        for action in data["review_actions"]
    )
    assert len(data["limitations"]) >= 3
    reloaded = db_session.get(CareerFact, active.id)
    assert reloaded is not None
    assert reloaded.status == "ACTIVE"
