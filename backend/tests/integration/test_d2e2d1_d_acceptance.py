"""D2-E2.D.1-D: multi-item human review acceptance against disposable PostgreSQL only.

The integration fixture resets the public schema of TEST_DATABASE_URL. It MUST
be provisioned as a new disposable database; never use Codespaces persistent DB.
"""

import json
import uuid
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.models import CareerFact, ResumeImportRecord, User
from app.services.career_facts import master_profile


def _user(db: Session) -> User:
    user = User(name="Acceptance Synthetic", email=f"accept-{uuid.uuid4()}@example.invalid")
    db.add(user)
    db.flush()
    return user


def _make_review(preview: dict[str, Any]) -> dict[str, Any]:
    items = []
    for item in preview["items"]:
        assert isinstance(item, dict)
        items.append(
            {
                **{
                    key: item[key]
                    for key in (
                        "draft_id",
                        "category",
                        "title",
                        "description",
                        "organization",
                        "start_date",
                        "end_date",
                        "source_excerpt",
                    )
                },
                "review_status": "confirmed",
            }
        )
    return {
        "preview_id": preview["preview_id"],
        "preview_ticket": preview["preview_ticket"],
        "confirmed": True,
        "items": items,
    }


def test_multi_role_preview_review_confirm_correct_history_and_isolation(
    api_client: TestClient, db_session: Session
) -> None:
    user = _user(db_session)
    other = _user(db_session)
    app = api_client.app
    assert isinstance(app, FastAPI)
    app.dependency_overrides[get_current_user] = lambda: user

    content = (
        "Pessoa inteiramente sintetica\n"
        "Contato: teste@example.invalid\n"
        "Experiencia profissional\n"
        "Empresa A | Assistente de Dados | 2022-2023\n"
        "Organizou planilhas de teste.\n"
        "Empresa A | Analista de Dados | 2023-2024\n"
        "Criou dashboards sinteticos de Power BI.\n"
        "Formacao academica\n"
        "Tecnologo em Dados | Faculdade Sintetica | 2024\n"
        "Habilidades\n"
        "Excel\n"
    )
    preview_res = api_client.post(
        "/api/v1/resume-imports/preview",
        files={"file": ("synthetic.txt", content.encode(), "text/plain")},
    )
    assert preview_res.status_code == 200
    preview = preview_res.json()
    experience = [i for i in preview["items"] if i["category"] == "experience"]
    assert len(experience) == 2
    assert experience[0]["title"] != experience[1]["title"]

    review = _make_review(preview)
    assert isinstance(review["items"], list)
    assert len(review["items"]) >= 3
    # User chooses to reject skills and edit one experience description.
    for item in review["items"]:
        if item["category"] == "skill":
            item["review_status"] = "rejected"
        elif item["category"] == "experience" and item["title"] == "Analista de Dados":
            item["description"] = "Dashboards auditados pelo candidato sintetico"
            item["review_status"] = "edited"

    confirm_res = api_client.post(
        "/api/v1/resume-imports/confirm",
        headers={"Idempotency-Key": "acceptance-multi-roles-0001"},
        json=review,
    )
    assert confirm_res.status_code == 201, confirm_res.text
    saved_ids = confirm_res.json()["created_fact_ids"]
    assert len(saved_ids) == len([x for x in review["items"] if x["review_status"] != "rejected"])
    receipt = db_session.scalar(
        select(ResumeImportRecord).where(ResumeImportRecord.user_id == user.id)
    )
    assert receipt is not None

    repeated = api_client.post(
        "/api/v1/resume-imports/confirm",
        headers={"Idempotency-Key": "acceptance-multi-roles-0001"},
        json=review,
    )
    assert repeated.status_code == 201
    assert repeated.json()["import_id"] == confirm_res.json()["import_id"]
    assert repeated.json()["created_fact_ids"] == saved_ids

    facts_res = api_client.get("/api/v1/career/facts")
    assert facts_res.status_code == 200
    assert len(facts_res.json()["items"]) == len(saved_ids)
    assert all(f["verification"] == "USER_DECLARED" for f in facts_res.json()["items"])
    assert all(f["predicate"] != "skill" for f in facts_res.json()["items"])
    assert len(master_profile(db_session, user.id)["items"]) == len(saved_ids)

    target = next(f for f in facts_res.json()["items"] if f["subject"] == "Analista de Dados")
    previous = json.loads(target["value"])
    correction = api_client.post(
        f"/api/v1/career/facts/{target['id']}/corrections",
        json={"value": "Corrigiu a descricao com revisao humana", "reason": "Ajuste sintetico"},
    )
    assert correction.status_code == 201, correction.text
    corrected = correction.json()
    assert corrected["supersedes_id"] == target["id"]
    assert corrected["verification"] == "USER_DECLARED"
    corrected_value = json.loads(corrected["value"])
    assert corrected_value["description"] == "Corrigiu a descricao com revisao humana"
    assert corrected_value["organization"] == previous["organization"]
    assert corrected_value["start_date"] == previous["start_date"]
    assert corrected_value["end_date"] == previous["end_date"]

    history = api_client.get("/api/v1/career/facts?include_history=true")
    assert history.status_code == 200
    old = next(f for f in history.json()["items"] if f["id"] == target["id"])
    assert old["status"] == "SUPERSEDED"
    assert len(history.json()["items"]) == len(saved_ids) + 1

    second_correction = api_client.post(
        f"/api/v1/career/facts/{target['id']}/corrections",
        json={"value": "Tentativa duplicada", "reason": "Nao pode"},
    )
    assert second_correction.status_code == 409
    assert len(api_client.get("/api/v1/career/facts").json()["items"]) == len(saved_ids)

    app.dependency_overrides[get_current_user] = lambda: other
    assert api_client.get("/api/v1/career/facts").json()["items"] == []
    assert api_client.get("/api/v1/career/profile").json()["items"] == []
    other_attempt = api_client.post(
        f"/api/v1/career/facts/{corrected['id']}/corrections",
        json={"value": "Tentativa outro usuario", "reason": "Sem permissao"},
    )
    assert other_attempt.status_code == 404
    # All tests here use a rollback-protected fixture, never a live account.
    assert db_session.scalar(select(CareerFact).where(CareerFact.user_id == other.id)) is None


def test_review_rejects_tampered_origin_before_writes(
    api_client: TestClient, db_session: Session
) -> None:
    user = _user(db_session)
    app = api_client.app
    assert isinstance(app, FastAPI)
    app.dependency_overrides[get_current_user] = lambda: user
    content = (
        "Curriculo sintetico para validacao\n"
        "Experiencia profissional\n"
        "Empresa Exemplo | Auxiliar | 2022-2023\n"
        "Planilhas internas sinteticas para testes.\n"
    )
    response = api_client.post(
        "/api/v1/resume-imports/preview",
        files={"file": ("cv.txt", content.encode(), "text/plain")},
    )
    assert response.status_code == 200
    review = _make_review(response.json())
    assert isinstance(review["items"], list)
    review["items"][0]["source_excerpt"] = "Fonte artificial adulterada"
    rejected = api_client.post(
        "/api/v1/resume-imports/confirm",
        headers={"Idempotency-Key": "acceptance-tampered-0001"},
        json=review,
    )
    assert rejected.status_code == 422
    assert (
        db_session.scalar(select(ResumeImportRecord).where(ResumeImportRecord.user_id == user.id))
        is None
    )
