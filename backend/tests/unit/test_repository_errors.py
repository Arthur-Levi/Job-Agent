from typing import Any, cast

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.repositories.errors import ConstraintViolationError, flush


class _Diag:
    constraint_name = "uq_something"


class _Orig(Exception):
    diag = _Diag()


class _Session:
    def __init__(self, error: Exception | None) -> None:
        self._error = error

    def flush(self) -> None:
        if self._error:
            raise self._error


def _flush(error: Exception | None) -> None:
    flush(cast(Session, _Session(error)))


def test_integrity_error_is_translated_with_constraint_name() -> None:
    with pytest.raises(ConstraintViolationError) as info:
        _flush(IntegrityError("INSERT", {}, _Orig()))
    assert info.value.constraint == "uq_something"


def test_constraint_name_is_none_when_driver_gives_no_diag() -> None:
    with pytest.raises(ConstraintViolationError) as info:
        _flush(IntegrityError("INSERT", {}, cast(Any, Exception("boom"))))
    assert info.value.constraint is None


def test_other_errors_pass_through() -> None:
    with pytest.raises(RuntimeError):
        _flush(RuntimeError("x"))
