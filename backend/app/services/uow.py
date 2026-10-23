from collections.abc import Iterator
from contextlib import contextmanager
from typing import Protocol


class UnitOfWork(Protocol):
    """Fronteira transacional que os services enxergam. `sqlalchemy.orm.Session` a satisfaz
    estruturalmente, então os services não importam SQLAlchemy."""

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


@contextmanager
def transactional(uow: UnitOfWork) -> Iterator[None]:
    """Tudo dentro do bloco é UMA transação: commit no sucesso, rollback em qualquer exceção."""
    try:
        yield
        uow.commit()
    except BaseException:
        uow.rollback()
        raise
