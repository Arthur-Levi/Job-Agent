from decimal import Decimal


def validate_salary(
    salary_min: Decimal | None, salary_max: Decimal | None, currency: str | None
) -> str | None:
    """Regra única de salário (schemas e services). Devolve a mensagem de erro ou None."""
    for value in (salary_min, salary_max):
        if value is not None and value < 0:
            return "salary values must be non-negative"
    if salary_min is not None and salary_max is not None and salary_min > salary_max:
        return "salary_min must be less than or equal to salary_max"
    if (salary_min is not None or salary_max is not None) and currency is None:
        return "currency is required when a salary is provided"
    return None
