import pytest

from tests.support import safe_test_database_url


def test_returns_none_when_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    assert safe_test_database_url() is None


def test_accepts_database_name_ending_in_test(monkeypatch: pytest.MonkeyPatch) -> None:
    url = "postgresql+psycopg://u:p@localhost:5432/job_agent_test"
    monkeypatch.setenv("TEST_DATABASE_URL", url)
    assert safe_test_database_url() == url


def test_rejects_non_test_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/job_agent")
    with pytest.raises(RuntimeError):
        safe_test_database_url()
