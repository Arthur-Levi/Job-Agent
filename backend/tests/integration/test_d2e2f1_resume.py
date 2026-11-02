"""D2-E2.F.1 acceptance tests: only ephemeral PostgreSQL from CI."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.models import CareerFact
from app.services.evidence_resume import resume_draft
from tests.integration.test_d2e2e_diagnostic import _fact, _user


def test_resume_draft_excludes_history_and_other_account(db_session: Session) -> None:
    a = _user(db_session)
    b = _user(db_session)
    active = _fact(
        db_session, a, title="Analista de Dados", category="experience",
        value='{"title":"Analista de Dados","description":"Criou painéis de teste",'
        '"organization":"Empresa Exemplo","start_date":"2023","end_date":"2024"}',
    )
    _fact(
        db_session, a, title="Trabalho antigo", category="experience",
        value='{"title":"Trabalho antigo","description":"Não mostrar",'
        '"organization":"Empresa Antiga","start_date":"2020","end_date":"2021"}',
        status="SUPERSEDED",
    )
    _fact(
        db_session, b, title="Competência secreta", category="skill",
        value='{"title":"Competência secreta","description":"Não mostrar"}',
    )
    result = resume_draft(db_session, a.id)
    experiences = result["sections"][0]["entries"]
    assert len(experiences) == 1
    assert experiences[0]["fact_id"] == str(active.id)
    assert experiences[0]["title"] == "Analista de Dados"
    assert experiences[0]["organization"] == "Empresa Exemplo"
    assert experiences[0]["start_date"] == "2023"
    assert experiences[0]["verification"] == "USER_DECLARED"
    assert "Trabalho antigo" not in str(result)
    assert "Competência secreta" not in str(result)
    assert result["status"] == "draft_requires_candidate_review"


def test_resume_draft_omits_unstructured_or_unsupported_without_invention(
    db_session: Session, api_client: TestClient
) -> None:
    user = _user(db_session)
    _fact(db_session, user, title="Título sem estrutura", category="experience", value="Texto livre")
    _fact(
        db_session, user, title="Projeto sintético", category="project",
        value='{"title":"Projeto sintético","description":"Aplicação de exemplo",'
        '"organization":null,"start_date":null,"end_date":null}',
    )
    _fact(
        db_session, user, title="Dado fora do escopo", category="other",
        value='{"title":"Dado fora do escopo"}',
    )
    app = api_client.app
    assert isinstance(app, FastAPI)
    app.dependency_overrides[get_current_user] = lambda: user
    response = api_client.get("/api/v1/career/resume-draft")
    assert response.status_code == 200
    body = response.json()
    assert body["sections"][0]["entries"] == []
    projects = body["sections"][2]["entries"]
    assert len(projects) == 1
    assert projects[0]["start_date"] is None
    assert projects[0]["end_date"] is None
    assert projects[0]["description"] == "Aplicação de exemplo"
    assert sorted(item["reason"] for item in body["omitted"]) == [
        "unstructured_fact", "unsupported_category"
    ]
    assert "Título sem estrutura" not in str(projects)
    assert "Dado fora do escopo" not in str(projects)
    assert db_session.query(CareerFact).filter(CareerFact.user_id == user.id).count() == 3


def test_empty_resume_draft_never_invents_content(db_session: Session) -> None:
    user = _user(db_session)
    result = resume_draft(db_session, user.id)
    assert all(section["entries"] == [] for section in result["sections"])
    assert result["omitted"] == []
