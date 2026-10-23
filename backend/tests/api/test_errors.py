from fastapi.testclient import TestClient


def test_unknown_route_uses_error_envelope(client: TestClient) -> None:
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "NOT_FOUND"
    assert error["details"] is None


def test_method_not_allowed_uses_error_envelope(client: TestClient) -> None:
    response = client.post("/health")
    assert response.status_code == 405
    assert response.json()["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_app_error_maps_status_code_and_details(client: TestClient) -> None:
    response = client.get("/__test/app-error")
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "THING_EXISTS"
    assert error["message"] == "Already exists"
    assert error["details"] == {"field": "name"}


def test_validation_error_returns_422_without_echoing_input(client: TestClient) -> None:
    response = client.post("/__test/echo", json={"name": 123456789})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"][0]["loc"] == ["body", "name"]
    assert "123456789" not in response.text


def test_malformed_json_returns_400(client: TestClient) -> None:
    response = client.post(
        "/__test/echo", content=b"{not json", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_JSON"


def test_unexpected_error_returns_500_without_leaking_details(
    client_no_raise: TestClient,
) -> None:
    response = client_no_raise.get("/__test/boom")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "super secret internal detail" not in response.text
    assert "Traceback" not in response.text
    assert response.headers["X-Request-ID"] == response.json()["error"]["request_id"]
