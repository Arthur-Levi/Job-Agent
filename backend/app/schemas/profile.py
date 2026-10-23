import uuid
from datetime import datetime

from app.domain.enums import Seniority, WorkModel
from app.schemas.common import (
    OptionalLongText,
    OptionalText100,
    OptionalText200,
    ReadModel,
    StrictModel,
)


class ProfileCreate(StrictModel):
    headline: OptionalText200 = None
    summary: OptionalLongText = None
    city: OptionalText100 = None
    state: OptionalText100 = None
    country: OptionalText100 = None
    desired_work_model: WorkModel | None = None
    desired_seniority: Seniority | None = None


class ProfileUpdate(ProfileCreate):
    """PATCH parcial: só campos enviados mudam; `null` explícito limpa o campo."""


class ProfileRead(ReadModel):
    id: uuid.UUID
    headline: str | None
    summary: str | None
    city: str | None
    state: str | None
    country: str | None
    desired_work_model: WorkModel | None
    desired_seniority: Seniority | None
    created_at: datetime
    updated_at: datetime
