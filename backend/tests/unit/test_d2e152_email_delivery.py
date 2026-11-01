"""D2-E1.5.2 Resend transport tests — no network, database or real credentials."""

import io
import json
import urllib.error
from typing import Any

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app
from app.services import email_delivery
from app.services.email_delivery import EmailDeliveryUnavailable, ResendMailer

DB = "postgresql+psycopg://u:p@localhost/test_db"
API_KEY = "re_TEST_ONLY_NOT_A_REAL_KEY"


class Response:
    status = 200

    def __enter__(self) -> "Response":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, n: int) -> bytes:
        return b'{"id":"synthetic-email-id"}'


class FakeOpener:
    def __init__(self, errors: list[int | str]) -> None:
        self.errors = errors
        self.requests: list[Any] = []

    def open(self, request: Any, timeout: float) -> Response:
        self.requests.append(request)
        assert timeout == 5
        if self.errors:
            failure = self.errors.pop(0)
            if failure == "network":
                raise urllib.error.URLError("Synthetic network failure")
            raise urllib.error.HTTPError(
                "https://api.resend.com/emails",
                int(failure),
                "Synthetic provider rejection",
                {},
                io.BytesIO(b"DO NOT LOG TOKEN OR API_KEY"),
            )
        return Response()


def _capture(monkeypatch: pytest.MonkeyPatch, failures: list[int | str]) -> FakeOpener:
    opener = FakeOpener(failures)
    monkeypatch.setattr(email_delivery.urllib.request, "build_opener", lambda *args: opener)
    monkeypatch.setattr(email_delivery.time, "sleep", lambda seconds: None)
    return opener


def test_resend_sends_text_only_with_auth_and_idempotency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opener = _capture(monkeypatch, [])
    mailer = ResendMailer(api_key=API_KEY, from_address="Job Agent <login@example.com>")
    link = "https://app.example.com/verify-email#token=TEST_TOKEN_ONLY"
    mailer.send("synthetic@example.com", "Confirme seu email", link)
    assert len(opener.requests) == 1
    request = opener.requests[0]
    headers = {key.lower(): value for key, value in request.header_items()}
    assert headers["authorization"] == f"Bearer {API_KEY}"
    assert headers["idempotency-key"].startswith("jobagent-")
    assert request.full_url == "https://api.resend.com/emails"
    payload = json.loads(request.data)
    assert payload["to"] == ["synthetic@example.com"]
    assert payload["from"] == "Job Agent <login@example.com>"
    assert link in payload["text"]
    assert "html" not in payload


def test_transient_errors_retry_using_same_idempotency_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opener = _capture(monkeypatch, [429, 503])
    ResendMailer(api_key=API_KEY, from_address="sender@example.com").send(
        "synthetic@example.com", "Recuperar acesso", "https://app.example.com/#token=TEST_ONLY"
    )
    assert len(opener.requests) == 3
    keys = [
        {key.lower(): value for key, value in request.header_items()}["idempotency-key"]
        for request in opener.requests
    ]
    assert len(set(keys)) == 1


@pytest.mark.parametrize("error", [400, 401, 403, 409, 422, 302])
def test_nonretryable_resend_errors_fail_closed(
    monkeypatch: pytest.MonkeyPatch, error: int,
) -> None:
    opener = _capture(monkeypatch, [error])
    with pytest.raises(EmailDeliveryUnavailable) as caught:
        ResendMailer(api_key=API_KEY, from_address="sender@example.com").send(
            "synthetic@example.com", "Confirmacao",
            "https://app.example.com/#token=TOP_SECRET_TEST_ONLY",
        )
    assert len(opener.requests) == 1
    assert "TOP_SECRET_TEST_ONLY" not in str(caught.value)
    assert API_KEY not in str(caught.value)


def test_network_retry_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    opener = _capture(monkeypatch, ["network", "network", "network"])
    with pytest.raises(EmailDeliveryUnavailable):
        ResendMailer(api_key=API_KEY, from_address="sender@example.com").send(
            "synthetic@example.com", "Confirmar", "https://app.example.com/#token=TEST"
        )
    assert len(opener.requests) == 3


def test_configuration_fails_closed_without_secrets() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None, database_url=DB, app_env="test",
            email_delivery_mode="resend", identity_lifecycle_enabled=True,
        )
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None, database_url=DB, app_env="production",
            email_delivery_mode="memory",
            registration_privacy_enabled=True,
            auth_rate_limit_enabled=True,
            auth_rate_limit_secret="Synthetic-TestOnly-Security-Key-1234567890",
        )


def test_resend_can_be_enabled_without_calling_network() -> None:
    settings = Settings(
        _env_file=None, database_url=DB, app_env="test",
        identity_lifecycle_enabled=True,
        email_delivery_mode="resend",
        resend_api_key=API_KEY,
        email_from_address="sender@example.com",
    )
    app = create_app(settings)
    assert isinstance(app.state.mailer, ResendMailer)
    assert app.state.mailer.api_key == API_KEY
