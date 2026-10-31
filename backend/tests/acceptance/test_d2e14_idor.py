"""D2-E1.4 direct-object authorization acceptance.

Foreign IDs must be invisible even when the client knows the UUID.
Only run on the guarded disposable PostgreSQL *_test integration fixture.
"""

from uuid import uuid4

from fastapi.testclient import TestClient


def _identity(client: TestClient, suffix: str) -> dict[str, str]:
    email = f"d2e14-{suffix}-{uuid4().hex}@example.com"
    password = "D2E14-synthetic-password-1234!"
    user = client.post(
        "/api/v1/auth/register",
        json={"name": f"Synthetic {suffix}", "email": email, "password": password},
    )
    assert user.status_code == 201
    token = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert token.status_code == 200
    return {"Authorization": "Bearer " + token.json()["access_token"]}


def test_d2e14_foreign_job_and_application_ids_are_denied(
    auth_client: TestClient,
) -> None:
    owner = _identity(auth_client, "owner")
    outsider = _identity(auth_client, "outsider")
    created = auth_client.post(
        "/api/v1/jobs",
        headers=owner,
        json={"title": "D2E14 Synthetic Job", "company": "Synthetic", "description": "test"},
    )
    assert created.status_code == 201
    job_id = created.json()["id"]
    application = auth_client.post("/api/v1/applications", headers=owner, json={"job_id": job_id})
    assert application.status_code == 201
    application_id = application.json()["id"]

    for method, route, payload in (
        ("get", f"/api/v1/jobs/{job_id}", None),
        ("patch", f"/api/v1/jobs/{job_id}", {"title": "Intrusion"}),
        ("delete", f"/api/v1/jobs/{job_id}", None),
        ("get", f"/api/v1/applications/{application_id}", None),
        ("patch", f"/api/v1/applications/{application_id}", {"notes": "Intrusion"}),
    ):
        response = getattr(auth_client, method)(
            route, headers=outsider, **({"json": payload} if payload is not None else {})
        )
        assert response.status_code == 404, (method, route, response.status_code)
    foreign_create = auth_client.post(
        "/api/v1/applications", headers=outsider, json={"job_id": job_id}
    )
    assert foreign_create.status_code == 422

    for route in (
        f"/api/v1/jobs/{job_id}",
        f"/api/v1/applications/{application_id}",
    ):
        response = auth_client.get(route)
        assert response.status_code == 401
    assert auth_client.get(f"/api/v1/jobs/{job_id}", headers=owner).status_code == 200
    assert (
        auth_client.get(f"/api/v1/applications/{application_id}", headers=owner).status_code == 200
    )
