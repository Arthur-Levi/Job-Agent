"""D2-E2.F.2: bounded, candidate-led vacancy requirements.

The candidate supplies requirements. This is not a scrape, verified vacancy,
employer/ATS decision or an estimate of hiring probability.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

RequirementCategory = Literal["skill", "experience", "education", "project", "work_mode"]
RequirementImportance = Literal["required", "preferred"]
WorkMode = Literal["remote_only", "onsite_only"]


def normalize_label(value: str) -> str:
    """Only exact case/whitespace normalization, never inferred synonyms."""
    return " ".join(value.casefold().split())


class VacancyRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    category: RequirementCategory
    name: str = Field(min_length=2, max_length=120)
    importance: RequirementImportance = "required"

    @field_validator("name")
    @classmethod
    def validate_label(cls, value: str) -> str:
        if not value.strip() or any(ord(char) < 32 for char in value):
            raise ValueError("Requirement must be nonblank and contain no control characters")
        return value

    @model_validator(mode="after")
    def validate_work_mode(self) -> "VacancyRequirement":
        if self.category == "work_mode" and self.name not in ("remote_only", "onsite_only"):
            raise ValueError("work_mode must be remote_only or onsite_only")
        return self


class VacancyMatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    vacancy_title: str = Field(min_length=2, max_length=160)
    requirements: list[VacancyRequirement] = Field(min_length=1, max_length=20)

    @field_validator("vacancy_title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        if not value.strip() or any(ord(char) < 32 for char in value):
            raise ValueError("Vacancy title must be nonblank and contain no control characters")
        return value

    @model_validator(mode="after")
    def reject_duplicate_requirements(self) -> "VacancyMatchRequest":
        keys = [(item.category, normalize_label(item.name)) for item in self.requirements]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate requirements are not allowed")
        return self
