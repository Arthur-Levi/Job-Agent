from fastapi.testclient import TestClient

ORIGIN = "http://localhost:5173"


def test_cors_allows_configured_origin_and_exposes_request_id(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": ORIGIN})
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert "x-request-id" in response.headers["access-control-expose-headers"].lower()


def test_cors_does_not_allow_unknown_origin(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in response.headers


def test_oversized_body_is_rejected_with_413(client: TestClient) -> None:
    response = client.post(
        "/__test/echo",
        content=b"x" * 2048,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"
    assert "x-request-id" in response.headers


def test_body_within_limit_is_accepted(client: TestClient) -> None:
    response = client.post("/__test/echo", json={"name": "ok"})
    assert response.status_code == 200
