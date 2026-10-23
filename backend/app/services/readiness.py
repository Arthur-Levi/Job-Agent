import logging
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReadinessReport:
    database_ok: bool


class ReadinessService:
    """Verifica dependências externas. Hoje: apenas conectividade com o PostgreSQL."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def check(self) -> ReadinessReport:
        try:
            self._session.execute(text("SELECT 1"))
        except SQLAlchemyError as exc:
            # Só o tipo do erro: a mensagem do driver pode conter host/usuário.
            logger.warning(
                "database readiness check failed", extra={"error_type": type(exc).__name__}
            )
            return ReadinessReport(database_ok=False)
        return ReadinessReport(database_ok=True)
