import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.integration.factories import make_job, make_user

JOB: dict[str, Any] = {
    "title": "Backend Developer",
    "company": "ACME",
    "description": "Build APIs.",
}
URL = "/api/v1/jobs"


def create(client: TestClient, **overrides: Any) -> dict[str, Any]:
    response = client.post(URL, json={**JOB, **overrides})
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def test_create_job(api_client: TestClient) -> None:
    body = create(
        api_client,
        source_url="https://jobs.example.com/1",
        work_model="REMOTE",
        salary_min="5000",
        salary_max="8000.50",
        currency="brl",
        published_at="2026-10-01T12:00:00Z",
    )
    uuid.UUID(body["id"])
    assert body["status"] == "OPEN"
    assert body["currency"] == "BRL"
    assert body["salary_max"] == "8000.50"  # dinheiro trafega como string
    assert body["source_url"] == "https://jobs.example.com/1"
    assert body["created_at"].endswith(("Z", "+00:00"))
    assert "user_id" not in body


def test_get_job(api_client: TestClient) -> None:
    created = create(api_client, description="Full description")
    response = api_client.get(f"{URL}/{created['id']}")
    assert response.status_code == 200
    assert response.json()["description"] == "Full description"


def test_list_jobs(api_client: TestClient) -> None:
    """Paginação sem lacunas nem duplicatas."""
    ids = {create(api_client, title=f"Job {i}")["id"] for i in range(5)}

    first = api_client.get(URL, params={"limit": 2, "offset": 0}).json()
    second = api_client.get(URL, params={"limit": 2, "offset": 2}).json()
    third = api_client.get(URL, params={"limit": 2, "offset": 4}).json()

    assert first["total"] == second["total"] == third["total"] == 5
    assert (first["limit"], second["offset"]) == (2, 2)
    seen = [job["id"] for page in (first, second, third) for job in page["items"]]
    assert len(seen) == 5
    assert set(seen) == ids


def test_list_jobs_defaults_and_status_filter(api_client: TestClient) -> None:
    create(api_client)
    closed = create(api_client, title="Old", status="CLOSED")
    default = api_client.get(URL).json()
    assert default["limit"] == 20
    assert default["total"] == 2
    filtered = api_client.get(URL, params={"status": "CLOSED"}).json()
    assert [job["id"] for job in filtered["items"]] == [closed["id"]]
    assert filtered["total"] == 1


@pytest.mark.parametrize(
    "params", [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"limit": "x"}, {"status": "NOPE"}]
)
def test_list_jobs_rejects_invalid_query(api_client: TestClient, params: dict[str, Any]) -> None:
    response = api_client.get(URL, params=params)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_update_job(api_client: TestClient) -> None:
    created = create(api_client, location="Remote", currency="BRL", salary_min="1000")
    response = api_client.patch(
        f"{URL}/{created['id']}",
        json={"title": "Senior Backend", "status": "CLOSED", "location": None},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Senior Backend"
    assert body["status"] == "CLOSED"
    assert body["location"] is None
    assert body["company"] == "ACME"  # intocado
    assert body["salary_min"] == "1000.00"


def test_update_job_validates_the_merged_salary(api_client: TestClient) -> None:
    created = create(api_client, salary_min="5000", salary_max="8000", currency="BRL")
    job_url = f"{URL}/{created['id']}"

    inverted = api_client.patch(job_url, json={"salary_max": "4000"})
    assert inverted.status_code == 422
    assert inverted.json()["error"]["code"] == "JOB_INVALID_SALARY"

    no_currency = api_client.patch(job_url, json={"currency": None})
    assert no_currency.status_code == 422
    assert no_currency.json()["error"]["code"] == "JOB_INVALID_SALARY"

    unchanged = api_client.get(job_url).json()
    assert (unchanged["salary_max"], unchanged["currency"]) == ("8000.00", "BRL")


def test_update_job_rejects_null_for_required_fields(api_client: TestClient) -> None:
    created = create(api_client)
    response = api_client.patch(f"{URL}/{created['id']}", json={"title": None})
    assert response.status_code == 422


def test_empty_patch_is_a_noop(api_client: TestClient) -> None:
    created = create(api_client)
    response = api_client.patch(f"{URL}/{created['id']}", json={})
    assert response.status_code == 200
    assert response.json()["title"] == created["title"]


def test_delete_job(api_client: TestClient) -> None:
    created = create(api_client)
    assert api_client.delete(f"{URL}/{created['id']}").status_code == 204
    assert api_client.get(f"{URL}/{created['id']}").status_code == 404


def test_delete_job_with_applications_is_409_and_keeps_the_job(api_client: TestClient) -> None:
    created = create(api_client)
    api_client.post("/api/v1/applications", json={"job_id": created["id"]})

    response = api_client.delete(f"{URL}/{created['id']}")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "JOB_HAS_APPLICATIONS"
    assert api_client.get(f"{URL}/{created['id']}").status_code == 200


def test_job_not_found(api_client: TestClient) -> None:
    missing = f"{URL}/{uuid.uuid4()}"
    for response in (
        api_client.get(missing),
        api_client.patch(missing, json={"title": "x"}),
        api_client.delete(missing),
    ):
        assert response.status_code == 404
        error = response.json()["error"]
        assert error["code"] == "JOB_NOT_FOUND"
        assert error["message"] == "Job not found"
    assert api_client.get(f"{URL}/not-a-uuid").status_code == 422


def test_job_of_another_user_is_404(api_client: TestClient, db_session: Session) -> None:
    other_job = make_job(db_session, make_user(db_session, email="other@example.com"))
    db_session.commit()
    assert api_client.get(f"{URL}/{other_job.id}").status_code == 404
    assert api_client.get(URL).json()["total"] == 0


def test_invalid_salary_range(api_client: TestClient) -> None:
    response = api_client.post(
        URL, json={**JOB, "salary_min": "9000", "salary_max": "5000", "currency": "BRL"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_duplicate_source_url_is_409_and_session_stays_usable(api_client: TestClient) -> None:
    create(api_client, source_url="https://jobs.example.com/dup")
    response = api_client.post(URL, json={**JOB, "source_url": "https://jobs.example.com/dup"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "JOB_SOURCE_URL_EXISTS"
    assert api_client.get(URL).json()["total"] == 1
    create(api_client, title="Another")


@pytest.mark.parametrize(
    "overrides",
    [
        {"title": "   "},
        {"title": "x" * 201},
        {"source_url": "javascript:alert(1)"},
        {"published_at": "2026-10-01T12:00:00"},  # sem timezone
        {"work_model": "MARS"},
        {"unknown_field": 1},
    ],
)
def test_create_job_validation_errors(api_client: TestClient, overrides: dict[str, Any]) -> None:
    response = api_client.post(URL, json={**JOB, **overrides})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_malformed_json_is_400(api_client: TestClient) -> None:
    response = api_client.post(URL, content=b"{oops", headers={"Content-Type": "application/json"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_JSON"
