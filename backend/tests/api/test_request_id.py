import re

from fastapi.testclient import TestClient

HEADER = "X-Request-ID"


def test_generates_request_id_when_absent(client: TestClient) -> None:
    response = client.get("/health")
    assert re.fullmatch(r"[0-9a-f]{32}", response.headers[HEADER])


def test_echoes_valid_client_request_id(client: TestClient) -> None:
    response = client.get("/health", headers={HEADER: "my-request-1234"})
    assert response.headers[HEADER] == "my-request-1234"


def test_replaces_invalid_client_request_id(client: TestClient) -> None:
    for bad in ("short", "has spaces in it!!", "x" * 65):
        response = client.get("/health", headers={HEADER: bad})
        assert response.headers[HEADER] != bad
        assert re.fullmatch(r"[0-9a-f]{32}", response.headers[HEADER])


def test_request_id_present_on_error_responses(client: TestClient) -> None:
    response = client.get("/nope", headers={HEADER: "trace-abcdef12"})
    assert response.status_code == 404
    assert response.headers[HEADER] == "trace-abcdef12"
    assert response.json()["error"]["request_id"] == "trace-abcdef12"
