from decimal import Decimal

import pytest

from app.domain.job_rules import validate_salary

D = Decimal


@pytest.mark.parametrize(
    ("low", "high", "currency"),
    [
        (None, None, None),
        (D(1), D(2), "BRL"),
        (D(5), D(5), "USD"),
        (D(1), None, "BRL"),
        (None, D(9), "EUR"),
    ],
)
def test_valid_combinations(
    low: Decimal | None, high: Decimal | None, currency: str | None
) -> None:
    assert validate_salary(low, high, currency) is None


@pytest.mark.parametrize(
    ("low", "high", "currency"),
    [(D(9), D(1), "BRL"), (D(1), None, None), (None, D(1), None), (D(-1), D(1), "BRL")],
)
def test_invalid_combinations(
    low: Decimal | None, high: Decimal | None, currency: str | None
) -> None:
    assert validate_salary(low, high, currency) is not None
