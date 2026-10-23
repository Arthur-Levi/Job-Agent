import uuid
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from tests.integration.factories import make_job, make_user

APPS = "/api/v1/applications"


def new_job(client: TestClient, title: str = "Backend Developer") -> str:
    response = client.post(
        "/api/v1/jobs", json={"title": title, "company": "ACME", "description": "d"}
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def new_application(client: TestClient, job_id: str | None = None) -> dict[str, Any]:
    response = client.post(APPS, json={"job_id": job_id or new_job(client)})
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def move(client: TestClient, application_id: str, status: str, **extra: Any) -> Any:
    return client.patch(f"{APPS}/{application_id}", json={"status": status, **extra})


def test_create_application(api_client: TestClient) -> None:
    job_id = new_job(api_client, "Python Developer")
    body = new_application(api_client, job_id)
    assert body["status"] == "DISCOVERED"
    assert body["job_id"] == job_id
    assert body["job"] == {"id": job_id, "title": "Python Developer", "company": "ACME"}
    assert body["applied_at"] is None
    assert body["allowed_next_statuses"] == ["QUALIFIED", "WITHDRAWN"]
    assert [e["event_type"] for e in body["events"]] == ["CREATED"]
    assert body["events"][0]["to_status"] == "DISCOVERED"
    assert body["events"][0]["from_status"] is None


def test_create_application_rejects_unknown_or_foreign_job(
    api_client: TestClient, db_session: Session
) -> None:
    for job_id in (
        str(uuid.uuid4()),
        str(make_job(db_session, make_user(db_session, email="o@example.com")).id),
    ):
        db_session.commit()
        response = api_client.post(APPS, json={"job_id": job_id})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_JOB_REFERENCE"


def test_create_application_twice_for_the_same_job_is_409(api_client: TestClient) -> None:
    job_id = new_job(api_client)
    new_application(api_client, job_id)
    response = api_client.post(APPS, json={"job_id": job_id})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "APPLICATION_ALREADY_EXISTS"
    assert api_client.get(APPS).json()["total"] == 1


def test_get_application_and_not_found(api_client: TestClient) -> None:
    created = new_application(api_client)
    assert api_client.get(f"{APPS}/{created['id']}").json()["id"] == created["id"]
    missing = api_client.get(f"{APPS}/{uuid.uuid4()}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "APPLICATION_NOT_FOUND"
    assert api_client.patch(f"{APPS}/{uuid.uuid4()}", json={"notes": "x"}).status_code == 404


def test_update_application_status(api_client: TestClient) -> None:
    created = new_application(api_client)
    response = move(api_client, created["id"], "QUALIFIED")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "QUALIFIED"
    assert body["updated_at"] >= created["updated_at"]


def test_invalid_application_status(api_client: TestClient) -> None:
    created = new_application(api_client)

    unknown = move(api_client, created["id"], "BOGUS")
    assert unknown.status_code == 422
    assert unknown.json()["error"]["code"] == "VALIDATION_ERROR"

    skipping = move(api_client, created["id"], "OFFER")  # pula etapas
    assert skipping.status_code == 409
    error = skipping.json()["error"]
    assert error["code"] == "INVALID_STATUS_TRANSITION"
    assert error["details"] == {
        "from": "DISCOVERED",
        "to": "OFFER",
        "allowed": ["QUALIFIED", "WITHDRAWN"],
    }

    after = api_client.get(f"{APPS}/{created['id']}").json()
    assert after["status"] == "DISCOVERED"  # nada mudou
    assert len(after["events"]) == 1  # e nenhum evento foi gravado


def test_application_status_creates_event(api_client: TestClient, db_session: Session) -> None:
    created = new_application(api_client)
    body = move(api_client, created["id"], "QUALIFIED").json()

    assert [e["event_type"] for e in body["events"]] == ["CREATED", "STATUS_CHANGED"]
    change = body["events"][1]
    assert (change["from_status"], change["to_status"]) == ("DISCOVERED", "QUALIFIED")
    assert change["metadata"] is None
    count = db_session.execute(
        text("SELECT count(*) FROM application_events WHERE application_id = :id"),
        {"id": created["id"]},
    ).scalar_one()
    assert count == 2


def test_forced_transition_is_allowed_and_flagged_in_the_event(api_client: TestClient) -> None:
    created = new_application(api_client)
    response = move(api_client, created["id"], "OFFER", force=True)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "OFFER"
    assert body["events"][-1]["metadata"] == {"forced": True}


def test_same_status_is_a_noop_without_event(api_client: TestClient) -> None:
    created = new_application(api_client)
    response = move(api_client, created["id"], "DISCOVERED")
    assert response.status_code == 200
    assert len(response.json()["events"]) == 1


def test_moving_to_applied_sets_applied_at_once(api_client: TestClient) -> None:
    created = new_application(api_client)
    for status in ("QUALIFIED", "PREPARED", "READY"):
        assert move(api_client, created["id"], status).status_code == 200
    applied = move(api_client, created["id"], "APPLIED").json()
    assert applied["applied_at"] is not None
    assert [e["to_status"] for e in applied["events"]] == [
        "DISCOVERED",
        "QUALIFIED",
        "PREPARED",
        "READY",
        "APPLIED",
    ]
    later = move(api_client, created["id"], "RESPONSE").json()
    assert later["applied_at"] == applied["applied_at"]


def test_explicit_applied_at_is_respected(api_client: TestClient) -> None:
    created = new_application(api_client)
    api_client.patch(f"{APPS}/{created['id']}", json={"applied_at": "2026-09-01T10:00:00Z"})
    for status in ("QUALIFIED", "PREPARED", "READY", "APPLIED"):
        body = move(api_client, created["id"], status).json()
    assert body["applied_at"].startswith("2026-09-01T10:00:00")


def test_notes_update_does_not_create_events(api_client: TestClient) -> None:
    created = new_application(api_client)
    body = api_client.patch(f"{APPS}/{created['id']}", json={"notes": "Call on Monday"}).json()
    assert body["notes"] == "Call on Monday"
    assert len(body["events"]) == 1
    cleared = api_client.patch(f"{APPS}/{created['id']}", json={"notes": None}).json()
    assert cleared["notes"] is None


def test_update_validation(api_client: TestClient) -> None:
    created = new_application(api_client)
    for payload in (
        {"force": True},
        {"status": None},
        {"unknown": 1},
        {"applied_at": "2026-01-01T00:00:00"},
    ):
        response = api_client.patch(f"{APPS}/{created['id']}", json=payload)
        assert response.status_code == 422, payload


def test_list_applications_with_filters_and_job_info(api_client: TestClient) -> None:
    first = new_application(api_client, new_job(api_client, "Job A"))
    second = new_application(api_client, new_job(api_client, "Job B"))
    move(api_client, second["id"], "QUALIFIED")

    everything = api_client.get(APPS).json()
    assert everything["total"] == 2
    assert {item["job"]["title"] for item in everything["items"]} == {"Job A", "Job B"}
    assert "events" not in everything["items"][0]
    by_title = {item["job"]["title"]: item for item in everything["items"]}
    assert by_title["Job A"]["allowed_next_statuses"] == ["QUALIFIED", "WITHDRAWN"]
    assert by_title["Job B"]["allowed_next_statuses"] == ["PREPARED", "WITHDRAWN"]

    qualified = api_client.get(APPS, params={"status": "QUALIFIED"}).json()
    assert [item["id"] for item in qualified["items"]] == [second["id"]]

    by_job = api_client.get(APPS, params={"job_id": first["job_id"]}).json()
    assert [item["id"] for item in by_job["items"]] == [first["id"]]

    assert api_client.get(APPS, params={"limit": 1}).json()["total"] == 2
    assert api_client.get(APPS, params={"limit": 101}).status_code == 422
    assert api_client.get(APPS, params={"status": "BOGUS"}).status_code == 422
