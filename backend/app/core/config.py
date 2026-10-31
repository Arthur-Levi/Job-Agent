import json
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy.engine import make_url

# backend/app/core/config.py -> raiz do repositório (onde fica o .env)
_REPO_ROOT = Path(__file__).resolve().parents[3]


class AppEnv(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Configuração central. Fonte: variáveis de ambiente (e .env na raiz do repo).

    DATABASE_URL é obrigatória e não tem default: falhar cedo é melhor que
    conectar silenciosamente num banco inesperado.
    """

    model_config = SettingsConfigDict(
        env_file=_REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        # Evita que ValidationError exiba o valor recebido (ex.: a URL com senha).
        hide_input_in_errors=True,
    )

    app_env: AppEnv = AppEnv.DEVELOPMENT
    app_name: str = "Job Agent"
    database_url: SecretStr
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )
    max_request_bytes: int = Field(default=1_048_576, ge=1024)
    db_connect_timeout_seconds: int = Field(default=5, ge=1)
    # Usuário único do D1: resolvido por e-mail e criado na primeira requisição (ver docs).
    default_user_email: str = Field(default="local@jobagent.local", min_length=3, max_length=320)
    default_user_name: str = Field(default="Local User", min_length=1, max_length=200)
    # D1-only test/dev compatibility. Never permitted in production.
    allow_legacy_local_user: bool = False

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalize_log_level(cls, value: Any) -> Any:
        return value.upper() if isinstance(value, str) else value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: Any) -> Any:
        if isinstance(value, str):
            raw = value.strip()
            if raw.startswith("["):
                return json.loads(raw)
            return [item.strip() for item in raw.split(",") if item.strip()]
        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_database_url(cls, value: Any) -> Any:
        if isinstance(value, SecretStr):
            value = value.get_secret_value()
        if not isinstance(value, str):
            raise ValueError("DATABASE_URL must be a string")
        # Mensagens de erro NUNCA incluem o valor (pode conter senha).
        if value.startswith("postgresql://"):
            # Sem driver explícito o SQLAlchemy assumiria psycopg2.
            value = value.replace("postgresql://", "postgresql+psycopg://", 1)
        if not value.startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL must be a PostgreSQL URL (postgresql+psycopg://...)")
        return value

    @model_validator(mode="after")
    def _forbid_wildcard_cors_in_production(self) -> Self:
        if self.app_env is AppEnv.PRODUCTION and "*" in self.cors_origins:
            raise ValueError("CORS_ORIGINS must not contain '*' when APP_ENV=production")
        if self.app_env is AppEnv.PRODUCTION and self.allow_legacy_local_user:
            raise ValueError("ALLOW_LEGACY_LOCAL_USER is forbidden in production")
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env is AppEnv.PRODUCTION

    @property
    def safe_database_url(self) -> str:
        """URL com a senha mascarada — única forma permitida de logar a conexão."""
        url = make_url(self.database_url.get_secret_value())
        return url.render_as_string(hide_password=True)
