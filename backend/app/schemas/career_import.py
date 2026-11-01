"""Pydantic contract for reviewed CV confirmation and Fact Ledger reads."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ConfirmedDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    draft_id: UUID
    category: Literal["experience", "education", "project", "skill"]
    title: str = Field(min_length=2, max_length=180)
    description: str = Field(min_length=1, max_length=4000)
    organization: str | None = Field(default=None, max_length=180)
    start_date: str | None = Field(default=None, max_length=12)
    end_date: str | None = Field(default=None, max_length=12)
    source_excerpt: str = Field(min_length=1, max_length=1200)
    review_status: Literal["confirmed", "edited", "rejected"]

    @model_validator(mode="after")
    def validate_dates(self) -> "ConfirmedDraft":
        import re

        for value in (self.start_date, self.end_date):
            if value and not re.fullmatch(
                r"(?:19|20)\d{2}(?:-(?:0[1-9]|1[0-2]))?|atual|presente",
                value,
                re.IGNORECASE,
            ):
                raise ValueError("Informe ano ou ano-mês, não uma data inferida")
        return self


class ImportConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preview_id: UUID
    preview_ticket: str = Field(min_length=40, max_length=125_000)
    confirmed: Literal[True]
    items: list[ConfirmedDraft] = Field(min_length=1, max_length=40)


class ConfirmResult(BaseModel):
    import_id: UUID
    created_fact_ids: list[UUID]
    skipped_duplicates: list[UUID]
    verification: Literal["USER_DECLARED"] = "USER_DECLARED"


class FactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    subject: str
    predicate: str
    value: str
    status: str
    verification: str
    source_reference: str
    supersedes_id: UUID | None
