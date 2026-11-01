"""End-to-end HTTP contract for reviewed CV with isolated PostgreSQL only."""

from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.models import User


def test_http_preview_confirm_and_read_fact(api_client: TestClient, db_session: Session) -> None:
    candidate = User(name="Synthetic CV", email=f"candidate-{uuid4()}@example.invalid")
    db_session.add(candidate)
    db_session.flush()
    app = api_client.app
    assert isinstance(app, FastAPI)
    app.dependency_overrides[get_current_user] = lambda: candidate
    content = (
        "Pessoa Sintética\n"
        "Email: synthetic@example.invalid\n"
        "Experiência profissional\n"
        "Empresa Fictícia | Analista de Dados | 2023-2024\n"
        "Criou dashboards com dados exclusivamente sintéticos.\n"
    )
    response = api_client.post(
        "/api/v1/resume-imports/preview",
        files={"file": ("cv.txt", content.encode(), "text/plain")},
    )
    assert response.status_code == 200, response.text
    preview = response.json()
    assert preview["preview_ticket"]
    assert preview["items"]
    assert response.headers["cache-control"] == "no-store"
    body = {
        "preview_id": preview["preview_id"],
        "preview_ticket": preview["preview_ticket"],
        "confirmed": True,
        "items": [
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
            for item in preview["items"]
        ],
    }
    confirmed = api_client.post(
        "/api/v1/resume-imports/confirm",
        headers={"Idempotency-Key": "synthetic-e2e-unique-001"},
        json=body,
    )
    assert confirmed.status_code == 201, confirmed.text
    assert confirmed.json()["created_fact_ids"]
    assert confirmed.headers["cache-control"] == "no-store"
    retry = api_client.post(
        "/api/v1/resume-imports/confirm",
        headers={"Idempotency-Key": "synthetic-e2e-unique-001"},
        json=body,
    )
    assert retry.status_code == 201
    assert confirmed.json()["import_id"] == retry.json()["import_id"]
    facts = api_client.get("/api/v1/career/facts")
    assert facts.status_code == 200
    assert len(facts.json()["items"]) == len(preview["items"])
    profile = api_client.get("/api/v1/career/profile")
    assert profile.status_code == 200
    assert profile.json()["items"]
