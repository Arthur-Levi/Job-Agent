import uuid
from datetime import datetime
from typing import Any, Self

from pydantic import AwareDatetime, Field, computed_field, model_validator

from app.domain.application_status import TRANSITIONS
from app.domain.enums import ApplicationEventType, ApplicationStatus
from app.schemas.common import OptionalLongText, ReadModel, StrictModel


class ApplicationCreate(StrictModel):
    """Toda candidatura nasce em DISCOVERED; o status evolui por PATCH (com evento)."""

    job_id: uuid.UUID
    notes: OptionalLongText = None


class ApplicationUpdate(StrictModel):
    status: ApplicationStatus | None = None
    notes: OptionalLongText = None
    applied_at: AwareDatetime | None = None
    # Correção administrativa: ignora a máquina de estados (registrado no evento).
    force: bool = False

    @model_validator(mode="after")
    def _check_payload(self) -> Self:
        if "status" in self.model_fields_set and self.status is None:
            raise ValueError("status cannot be null")
        if self.force and self.status is None:
            raise ValueError("force requires status")
        return self


class JobSummary(ReadModel):
    id: uuid.UUID
    title: str
    company: str


class ApplicationRead(ReadModel):
    id: uuid.UUID
    job_id: uuid.UUID
    job: JobSummary
    status: ApplicationStatus
    applied_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def allowed_next_statuses(self) -> list[ApplicationStatus]:
        """Destinos permitidos SEM `force` (fonte única: a máquina de estados do domínio).
        O frontend usa esta lista em vez de duplicar a política."""
        return sorted(TRANSITIONS[self.status], key=list(ApplicationStatus).index)


class ApplicationEventRead(ReadModel):
    id: uuid.UUID
    event_type: ApplicationEventType
    from_status: ApplicationStatus | None
    to_status: ApplicationStatus | None
    # Atributo ORM = event_metadata (a coluna se chama "metadata").
    metadata: dict[str, Any] | None = Field(default=None, validation_alias="event_metadata")
    created_at: datetime


class ApplicationDetail(ApplicationRead):
    events: list[ApplicationEventRead]
