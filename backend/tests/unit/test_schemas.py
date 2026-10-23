from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from app.domain.enums import JobStatus
from app.schemas.application import ApplicationUpdate
from app.schemas.job import JobCreate, JobUpdate
from app.schemas.profile import ProfileCreate

VALID: dict[str, Any] = {"title": "Dev", "company": "ACME", "description": "Build things."}


def job(**overrides: Any) -> JobCreate:
    return JobCreate(**{**VALID, **overrides})


def test_strings_are_trimmed_and_blank_required_strings_rejected() -> None:
    assert job(title="  Dev  ").title == "Dev"
    for field in ("title", "company", "description"):
        with pytest.raises(ValidationError):
            job(**{field: "   "})


def test_required_string_max_length() -> None:
    with pytest.raises(ValidationError):
        job(title="x" * 201)


def test_blank_optional_strings_become_none() -> None:
    created = job(location="   ", source="", source_url=" ", currency="")
    assert created.location is None
    assert created.source is None
    assert created.source_url is None
    assert created.currency is None


@pytest.mark.parametrize(
    "url", ["javascript:alert(1)", "ftp://x.com/a", "not a url", "file:///etc/passwd"]
)
def test_non_http_urls_are_rejected(url: str) -> None:
    with pytest.raises(ValidationError):
        job(source_url=url)


def test_url_is_validated_and_normalized() -> None:
    assert job(source_url=" https://jobs.example.com ").source_url == "https://jobs.example.com/"


def test_currency_is_uppercased_and_validated() -> None:
    assert job(salary_min=1, currency="brl").currency == "BRL"
    with pytest.raises(ValidationError):
        job(currency="REAL")


def test_salary_rules() -> None:
    assert job(salary_min=Decimal("100.50"), salary_max=200, currency="BRL").salary_max == 200
    for bad in (
        {"salary_min": 10, "salary_max": 5, "currency": "BRL"},  # min > max
        {"salary_min": 10},  # sem moeda
        {"salary_min": -1, "currency": "BRL"},
        {"salary_min": "1.234", "currency": "BRL"},  # 3 casas decimais
        {"salary_min": "NaN", "currency": "BRL"},
    ):
        with pytest.raises(ValidationError):
            job(**bad)


def test_published_at_must_be_timezone_aware() -> None:
    with pytest.raises(ValidationError):
        job(published_at="2026-01-01T10:00:00")
    assert job(published_at="2026-01-01T10:00:00Z").published_at is not None


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        job(titel="typo")


def test_invalid_enum_is_rejected() -> None:
    with pytest.raises(ValidationError):
        job(status="DELETED")
    assert job().status is JobStatus.OPEN


def test_job_update_distinguishes_absent_from_explicit_null() -> None:
    update = JobUpdate.model_validate({"location": None})
    assert update.model_dump(exclude_unset=True) == {"location": None}
    assert JobUpdate.model_validate({}).model_dump(exclude_unset=True) == {}


@pytest.mark.parametrize("field", ["title", "company", "description", "status"])
def test_job_update_rejects_null_for_required_fields(field: str) -> None:
    with pytest.raises(ValidationError):
        JobUpdate.model_validate({field: None})


def test_job_update_rejects_inverted_salary_in_payload() -> None:
    with pytest.raises(ValidationError):
        JobUpdate.model_validate({"salary_min": 10, "salary_max": 5})


def test_application_update_rules() -> None:
    with pytest.raises(ValidationError):
        ApplicationUpdate.model_validate({"status": None})
    with pytest.raises(ValidationError):
        ApplicationUpdate.model_validate({"force": True})
    with pytest.raises(ValidationError):
        ApplicationUpdate.model_validate({"status": "BOGUS"})
    assert ApplicationUpdate.model_validate({"status": "QUALIFIED", "force": True}).force


def test_profile_all_fields_optional_and_enums_validated() -> None:
    assert ProfileCreate().headline is None
    with pytest.raises(ValidationError):
        ProfileCreate.model_validate({"desired_work_model": "MARS"})
