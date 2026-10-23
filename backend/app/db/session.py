from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings


class Database:
    """Dono do engine e da fábrica de sessões. Criado uma vez por aplicação.

    Convenção de transação: quem decide o commit é o SERVICE (caso de uso),
    explicitamente. A sessão por request nunca faz commit sozinha — assim o commit
    acontece antes da resposta ser enviada e uma operação composta (ex.: mudar status
    + gravar evento) é atômica por construção.
    """

    def __init__(self, settings: Settings) -> None:
        self._engine: Engine = create_engine(
            settings.database_url.get_secret_value(),
            pool_pre_ping=True,
            connect_args={"connect_timeout": settings.db_connect_timeout_seconds},
        )
        self._session_factory = sessionmaker(bind=self._engine, expire_on_commit=False)

    @property
    def engine(self) -> Engine:
        return self._engine

    def new_session(self) -> Session:
        return self._session_factory()

    @contextmanager
    def session_scope(self) -> Iterator[Session]:
        """Para scripts/seed fora do ciclo HTTP: commit no sucesso, rollback no erro."""
        session = self.new_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def dispose(self) -> None:
        self._engine.dispose()
