import pytest

from app.core.config import Settings
from app.devtools import seed
from app.devtools.seed import SeedNotAllowedError, ensure_development

URL = "postgresql+psycopg://u:p@localhost/x_test"


def settings_for(env: str) -> Settings:
    return Settings(
        _env_file=None,
        app_env=env,
        database_url=URL,
        auth_rate_limit_enabled=(env == "production"),
        registration_privacy_enabled=(env == "production"),
        auth_rate_limit_secret="Synthetic-TestOnly-Security-Key-1234567890",
    )


@pytest.mark.parametrize("env", ["production", "test"])
def test_seed_is_refused_outside_development(env: str) -> None:
    with pytest.raises(SeedNotAllowedError):
        ensure_development(settings_for(env))


def test_seed_is_allowed_in_development() -> None:
    ensure_development(settings_for("development"))


def test_seed_cli_refuses_production_before_touching_the_database(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", URL)
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("AUTH_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("REGISTRATION_PRIVACY_ENABLED", "true")
    monkeypatch.setenv("AUTH_RATE_LIMIT_SECRET", "Synthetic-TestOnly-Security-Key-1234567890")

    assert seed.main() == 2
    assert "only allowed with APP_ENV=development" in capsys.readouterr().err


def test_seed_sample_data_is_obviously_fictional() -> None:
    for job in seed._seed_jobs():
        assert job.source == seed.SEED_SOURCE
        assert job.source_url is not None
        assert ".invalid/" in job.source_url  # TLD reservado: nunca resolve
        assert "[DEV SEED]" in job.description
        assert "(sample)" in job.title
