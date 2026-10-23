import uuid
from datetime import datetime
from decimal import Decimal
from typing import Self

from pydantic import AwareDatetime, model_validator

from app.domain.enums import EmploymentType, JobStatus, Seniority, WorkModel
from app.domain.job_rules import validate_salary
from app.schemas.common import (
    CurrencyCode,
    Money,
    OptionalText100,
    OptionalText200,
    OptionalUrl,
    ReadModel,
    RequiredName,
    RequiredText,
    StrictModel,
)

_NOT_NULLABLE = ("title", "company", "description", "status")


class JobCreate(StrictModel):
    title: RequiredName
    company: RequiredName
    description: RequiredText
    source: OptionalText100 = None
    source_url: OptionalUrl = None
    location: OptionalText200 = None
    work_model: WorkModel | None = None
    employment_type: EmploymentType | None = None
    seniority: Seniority | None = None
    salary_min: Money = None
    salary_max: Money = None
    currency: CurrencyCode = None
    published_at: AwareDatetime | None = None
    status: JobStatus = JobStatus.OPEN

    @model_validator(mode="after")
    def _check_salary(self) -> Self:
        error = validate_salary(self.salary_min, self.salary_max, self.currency)
        if error:
            raise ValueError(error)
        return self


class JobUpdate(StrictModel):
    """PATCH parcial. `null` explícito limpa campos opcionais e é rejeitado nos obrigatórios.

    A regra de salário sobre o estado MESCLADO (campos enviados + já gravados) é aplicada no
    service; aqui só se valida o que veio no próprio payload.
    """

    title: RequiredName | None = None
    company: RequiredName | None = None
    description: RequiredText | None = None
    source: OptionalText100 = None
    source_url: OptionalUrl = None
    location: OptionalText200 = None
    work_model: WorkModel | None = None
    employment_type: EmploymentType | None = None
    seniority: Seniority | None = None
    salary_min: Money = None
    salary_max: Money = None
    currency: CurrencyCode = None
    published_at: AwareDatetime | None = None
    status: JobStatus | None = None

    @model_validator(mode="after")
    def _check_payload(self) -> Self:
        for name in _NOT_NULLABLE:
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        low, high = self.salary_min, self.salary_max
        if low is not None and high is not None and low > high:
            raise ValueError("salary_min must be less than or equal to salary_max")
        return self


class JobRead(ReadModel):
    id: uuid.UUID
    title: str
    company: str
    description: str
    source: str | None
    source_url: str | None
    location: str | None
    work_model: WorkModel | None
    employment_type: EmploymentType | None
    seniority: Seniority | None
    salary_min: Decimal | None
    salary_max: Decimal | None
    currency: str | None
    published_at: datetime | None
    status: JobStatus
    created_at: datetime
    updated_at: datetime
