"""D2-E1 — RED-first multi-tenant acceptance specification.

Not a PASS claim: these tests MUST fail before auth routes and ownership are implemented.
Run only against a verified, disposable React PostgreSQL test DB. The integration
fixture recreates the public schema on first use.
"""

import json
from datetime import timedelta
from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuthSession
from app.services.auth import digest, now_utc

PERSONAS: list[dict[str, Any]] = cast(
    list[dict[str, Any]],
    json.loads((Path(__file__).with_name("d2e_personas.json")).read_text(encoding="utf-8"))[
        "personas"
    ],
)


def credentials(persona: dict[str, Any]) -> dict[str, str]:
    # Test-only password, never a user/production credential.
    return {"email": persona["email"], "password": f"TestOnly-D2E1-{persona['id']}-not-for-prod!"}


def token(client: TestClient, persona: dict[str, Any]) -> str:
    response = client.post("/api/v1/auth/login", json=credentials(persona))
    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data.get("access_token"), str) and len(data["access_token"]) >= 32
    assert data.get("token_type", "").lower() == "bearer"
    return str(data["access_token"])


def headers(token_value: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_value}"}


def test_e1_no_default_identity_and_unauthenticated_requests_blocked(
    auth_client: TestClient,
) -> None:
    # The current D1 default-user route returns 200, so this intentionally starts RED.
    for path in ("/api/v1/profile", "/api/v1/jobs", "/api/v1/applications"):
        response = auth_client.get(path)
        assert response.status_code == 401, (path, response.status_code, response.text)


def test_e1_ten_accounts_are_distinct_and_own_their_profiles(auth_client: TestClient) -> None:
    for persona in PERSONAS:
        response = auth_client.post(
            "/api/v1/auth/register", json={**credentials(persona), "name": persona["name"]}
        )
        assert response.status_code == 201, (persona["id"], response.status_code, response.text)

    ids = set()
    for persona in PERSONAS:
        auth = headers(token(auth_client, persona))
        me = auth_client.get("/api/v1/auth/me", headers=auth)
        assert me.status_code == 200, me.text
        assert me.json()["email"].lower() == persona["email"]
        ids.add(me.json()["id"])
        profile = auth_client.post(
            "/api/v1/profile",
            headers=auth,
            json={"headline": persona["target_role"]},
        )
        assert profile.status_code == 201, (persona["id"], profile.text)
        assert (
            auth_client.get("/api/v1/profile", headers=auth).json()["headline"]
            == persona["target_role"]
        )
    assert len(ids) == 10


def test_e1_cross_user_jobs_are_not_exposed(auth_client: TestClient) -> None:
    # Independent from previous test: never rely on test execution order.
    identities = []
    for persona in PERSONAS:
        registered = auth_client.post(
            "/api/v1/auth/register", json={**credentials(persona), "name": persona["name"]}
        )
        assert registered.status_code == 201, (persona["id"], registered.text)
        identities.append(headers(token(auth_client, persona)))

    job_ids = []
    for persona, auth in zip(PERSONAS, identities, strict=True):
        job = auth_client.post(
            "/api/v1/jobs",
            headers=auth,
            json={
                "title": persona["job"]["title"],
                "company": persona["job"]["company"],
                "description": "Synthetic D2-E1 isolation scenario",
            },
        )
        assert job.status_code == 201, job.text
        job_ids.append(job.json()["id"])

    for i, auth in enumerate(identities):
        own_jobs = auth_client.get("/api/v1/jobs", headers=auth)
        assert own_jobs.status_code == 200
        assert {x["id"] for x in own_jobs.json()["items"]} == {job_ids[i]}
        for j, job_id in enumerate(job_ids):
            if i != j:
                foreign = auth_client.get(f"/api/v1/jobs/{job_id}", headers=auth)
                assert foreign.status_code == 404, (i, j, foreign.status_code)


def test_e1_logout_revokes_only_its_own_session(auth_client: TestClient) -> None:
    first, second = PERSONAS[:2]
    for persona in (first, second):
        response = auth_client.post(
            "/api/v1/auth/register", json={**credentials(persona), "name": persona["name"]}
        )
        assert response.status_code == 201
    a, b = token(auth_client, first), token(auth_client, second)
    assert auth_client.post("/api/v1/auth/logout", headers=headers(a)).status_code in (200, 204)
    assert auth_client.get("/api/v1/auth/me", headers=headers(a)).status_code == 401
    assert auth_client.get("/api/v1/auth/me", headers=headers(b)).status_code == 200


def test_e1_duplicate_registration_wrong_password_and_invalid_token(
    auth_client: TestClient,
) -> None:
    persona = PERSONAS[0]
    data = {**credentials(persona), "name": persona["name"]}
    created = auth_client.post("/api/v1/auth/register", json=data)
    assert created.status_code == 201, created.text
    repeated = auth_client.post("/api/v1/auth/register", json=data)
    assert repeated.status_code == 409
    bad = auth_client.post(
        "/api/v1/auth/login", json={**credentials(persona), "password": "wrong-password"}
    )
    assert bad.status_code == 401
    assert (
        auth_client.get(
            "/api/v1/auth/me", headers=headers("bogus-auth-token-that-is-not-valid")
        ).status_code
        == 401
    )
    correct = headers(token(auth_client, persona))
    assert auth_client.get("/api/v1/auth/me", headers=correct).status_code == 200


def test_e1_session_expiry_revokes_access(auth_client: TestClient, db_session: Session) -> None:
    persona = PERSONAS[1]
    assert (
        auth_client.post(
            "/api/v1/auth/register", json={**credentials(persona), "name": persona["name"]}
        ).status_code
        == 201
    )
    bearer_token = token(auth_client, persona)
    session = db_session.execute(
        select(AuthSession).where(AuthSession.token_hash == digest(bearer_token))
    ).scalar_one()
    session.expires_at = now_utc() - timedelta(seconds=1)
    db_session.flush()
    assert auth_client.get("/api/v1/auth/me", headers=headers(bearer_token)).status_code == 401
