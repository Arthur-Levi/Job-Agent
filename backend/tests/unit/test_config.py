import pytest
from pydantic import ValidationError

from app.core.config import Settings

URL = "postgresql+psycopg://user:s3cretpw@db.example.com:5432/job_agent"


def make(**overrides: object) -> Settings:
    return Settings(_env_file=None, database_url=URL, **overrides)  # type: ignore[arg-type]


def test_cors_origins_parsed_from_comma_separated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://a.com, http://b.com ,")
    assert make().cors_origins == ["http://a.com", "http://b.com"]


def test_wildcard_cors_rejected_in_production() -> None:
    with pytest.raises(ValidationError):
        make(app_env="production", cors_origins=["*"])


def test_wildcard_cors_allowed_outside_production() -> None:
    assert make(app_env="development", cors_origins=["*"]).cors_origins == ["*"]


def test_plain_postgresql_scheme_is_normalized_to_psycopg() -> None:
    settings = Settings(_env_file=None, database_url="postgresql://u:p@localhost/db")
    assert settings.database_url.get_secret_value().startswith("postgresql+psycopg://")


def test_safe_database_url_masks_password() -> None:
    assert "s3cretpw" not in make().safe_database_url


def test_database_url_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_invalid_database_url_error_does_not_leak_the_url() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None, database_url="mysql://user:leakme@host/db")
    assert "leakme" not in str(exc_info.value)


def test_log_level_is_case_insensitive() -> None:
    assert make(log_level="debug").log_level == "DEBUG"
