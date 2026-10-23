from fastapi.testclient import TestClient


def test_get_profile_before_creation_is_404(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/profile")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROFILE_NOT_FOUND"


def test_create_profile(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/profile",
        json={
            "headline": "  Backend Developer ",
            "city": "São Paulo",
            "country": "Brasil",
            "desired_work_model": "REMOTE",
            "desired_seniority": "JUNIOR",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["headline"] == "Backend Developer"
    assert body["desired_work_model"] == "REMOTE"
    assert body["summary"] is None
    assert body["created_at"].endswith(("Z", "+00:00"))


def test_create_profile_twice_is_409(api_client: TestClient) -> None:
    assert api_client.post("/api/v1/profile", json={}).status_code == 201
    response = api_client.post("/api/v1/profile", json={})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PROFILE_ALREADY_EXISTS"
    assert api_client.get("/api/v1/profile").status_code == 200  # sessão continua utilizável


def test_get_profile(api_client: TestClient) -> None:
    created = api_client.post("/api/v1/profile", json={"headline": "Dev"}).json()
    response = api_client.get("/api/v1/profile")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_update_profile(api_client: TestClient) -> None:
    """PATCH parcial: ausente = intocado; null explícito limpa."""
    api_client.post("/api/v1/profile", json={"headline": "Dev", "city": "Recife"})
    response = api_client.patch("/api/v1/profile", json={"summary": "Hello", "city": None})
    assert response.status_code == 200
    body = response.json()
    assert body["headline"] == "Dev"  # intocado
    assert body["summary"] == "Hello"
    assert body["city"] is None  # null explícito limpa
    assert body["updated_at"] >= body["created_at"]


def test_update_profile_without_profile_is_404(api_client: TestClient) -> None:
    response = api_client.patch("/api/v1/profile", json={"headline": "x"})
    assert response.status_code == 404


def test_profile_validation_errors_use_the_envelope(api_client: TestClient) -> None:
    for payload in ({"desired_work_model": "MARS"}, {"headline": "x" * 201}, {"nope": 1}):
        response = api_client.post("/api/v1/profile", json=payload)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_blank_optional_field_is_stored_as_null(api_client: TestClient) -> None:
    body = api_client.post("/api/v1/profile", json={"headline": "   "}).json()
    assert body["headline"] is None
