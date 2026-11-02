"""D2-E2.F.2 contract tests on synthetic disposable PostgreSQL only.

Integration fixture drops the public schema: never point this at a saved DB.
"""

import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.models import CareerFact
from app.schemas.vacancy_match import VacancyMatchRequest
from app.services.vacancy_matching import vacancy_match
from tests.integration.test_d2e2e_diagnostic import _fact, _user


def _requirement(category: str, name: str, importance: str = "required") -> dict[str, str]:
    return {"category": category, "name": name, "importance": importance}


def test_exact_match_unknown_and_isolation_via_api(
    api_client: TestClient, db_session: Session
) -> None:
    candidate = _user(db_session)
    other = _user(db_session)
    matched = _fact(
        db_session,
        candidate,
        title="Excel",
        category="skill",
        value=json.dumps({"title": "Excel", "description": "Planilhas de exemplo"}),
    )
    _fact(
        db_session,
        other,
        title="Python",
        category="skill",
        value=json.dumps({"title": "Python", "description": "Apenas outra conta"}),
    )
    _fact(
        db_session,
        candidate,
        title="SQL",
        category="skill",
        value=json.dumps({"title": "SQL", "description": "Já substituído"}),
        status="SUPERSEDED",
    )
    _fact(
        db_session,
        candidate,
        title="Power BI",
        category="skill",
        value="Power BI",  # not structured, cannot be claimed as verified match
    )
    app = api_client.app
    assert isinstance(app, FastAPI)
    app.dependency_overrides[get_current_user] = lambda: candidate
    request = {
        "vacancy_title": "Assistente de Dados",
        "requirements": [
            _requirement("skill", "  eXcEl  "),
            _requirement("skill", "Python"),
            _requirement("skill", "SQL"),
            _requirement("skill", "Power BI"),
            _requirement("experience", "Analista de Dados", "preferred"),
        ],
    }
    response = api_client.post("/api/v1/career/vacancy-match", json=request)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["vacancy_source"] == "candidate_supplied_unverified"
    assert data["summary"] == {
        "total": 5, "documented_match": 1,
        "not_documented": 4, "explicit_incompatibility": 0,
    }
    first = data["requirements"][0]
    assert first["classification"] == "documented_match"
    assert first["evidence"] == [
        {"fact_id": str(matched.id), "title": "Excel", "verification": "USER_DECLARED"}
    ]
    assert all(item["evidence"] == [] for item in data["requirements"][1:])
    assert all(item["classification"] == "not_documented" for item in data["requirements"][1:])
    assert "Python" not in str(first["evidence"])
    assert "score" not in data
    assert "chance" not in str(data["summary"])
    assert db_session.query(CareerFact).filter(CareerFact.user_id == candidate.id).count() == 3


def test_work_mode_conflicts_only_when_an_explicit_fact_disagrees(db_session: Session) -> None:
    candidate = _user(db_session)
    own_mode = _fact(
        db_session,
        candidate,
        title="Modalidade declarada",
        category="work_mode",
        value=json.dumps({"mode": "remote_only"}),
    )
    request = VacancyMatchRequest.model_validate(
        {
            "vacancy_title": "Vaga no escritório",
            "requirements": [
                _requirement("work_mode", "onsite_only"),
                _requirement("work_mode", "remote_only", "preferred"),
                _requirement("skill", "Kubernetes"),
            ],
        }
    )
    result = vacancy_match(db_session, candidate.id, request)
    assert [item["classification"] for item in result["requirements"]] == [
        "explicit_incompatibility", "documented_match", "not_documented",
    ]
    assert result["requirements"][0]["evidence"][0]["fact_id"] == str(own_mode.id)
    assert "inelegibilidade" in result["requirements"][0]["next_step"]
    assert result["summary"]["explicit_incompatibility"] == 1


def test_competing_or_unstructured_modes_do_not_produce_false_conflicts(
    db_session: Session,
) -> None:
    candidate = _user(db_session)
    _fact(
        db_session, candidate, title="Remoto", category="work_mode",
        value=json.dumps({"mode": "remote_only"}),
    )
    _fact(
        db_session, candidate, title="Presencial", category="work_mode",
        value=json.dumps({"mode": "onsite_only"}),
    )
    _fact(
        db_session, candidate, title="Modo malformado", category="work_mode",
        value=json.dumps({"mode": ["remote_only"]}),
    )
    request = VacancyMatchRequest.model_validate(
        {"vacancy_title": "Vaga híbrida", "requirements": [_requirement("work_mode", "remote_only")]}
    )
    data = vacancy_match(db_session, candidate.id, request)
    assert data["requirements"][0]["classification"] == "not_documented"
    assert data["requirements"][0]["evidence"] == []
    assert "contraditórios" in data["requirements"][0]["explanation"]


def test_validation_rejects_duplicate_and_unsupported_requirements(
    api_client: TestClient, db_session: Session
) -> None:
    user = _user(db_session)
    app = api_client.app
    assert isinstance(app, FastAPI)
    app.dependency_overrides[get_current_user] = lambda: user
    duplicate = {
        "vacancy_title": "Vaga sintética",
        "requirements": [_requirement("skill", "Python"), _requirement("skill", " python ")],
    }
    assert api_client.post("/api/v1/career/vacancy-match", json=duplicate).status_code == 422
    bad_mode = {
        "vacancy_title": "Vaga sintética",
        "requirements": [_requirement("work_mode", "hybrid_required")],
    }
    assert api_client.post("/api/v1/career/vacancy-match", json=bad_mode).status_code == 422
    oversized = {
        "vacancy_title": "Vaga sintética",
        "requirements": [_requirement("skill", f"Competência {i}") for i in range(21)],
    }
    assert api_client.post("/api/v1/career/vacancy-match", json=oversized).status_code == 422
    extra = {
        "vacancy_title": "Vaga sintética",
        "requirements": [_requirement("skill", "Python")],
        "candidate_fact_ids": ["forged"],
    }
    assert api_client.post("/api/v1/career/vacancy-match", json=extra).status_code == 422


def test_missing_records_must_not_be_interpreted_as_candidate_rejection(
    db_session: Session,
) -> None:
    user = _user(db_session)
    payload = VacancyMatchRequest.model_validate(
        {"vacancy_title": "Vaga sintética", "requirements": [_requirement("skill", "Python")]}
    )
    result = vacancy_match(db_session, user.id, payload)
    assert result["requirements"][0]["classification"] == "not_documented"
    assert result["summary"]["documented_match"] == 0
    assert result["summary"]["explicit_incompatibility"] == 0
    assert result["status"] == "preliminary_candidate_review"
