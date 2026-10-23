"""Enums de domínio. Puro Python: sem dependência de SQLAlchemy/FastAPI.

Valor == nome (maiúsculo). No banco são VARCHAR + CHECK (não enums nativos do PostgreSQL):
adicionar um valor é "recriar a CHECK" numa migration, sem o atrito de ALTER TYPE.
"""

from enum import StrEnum


class WorkModel(StrEnum):
    REMOTE = "REMOTE"
    HYBRID = "HYBRID"
    ONSITE = "ONSITE"


class Seniority(StrEnum):
    INTERN = "INTERN"
    JUNIOR = "JUNIOR"
    MID = "MID"
    SENIOR = "SENIOR"
    LEAD = "LEAD"


class EmploymentType(StrEnum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    CONTRACT = "CONTRACT"
    INTERNSHIP = "INTERNSHIP"
    TEMPORARY = "TEMPORARY"
    FREELANCE = "FREELANCE"


class SkillProficiency(StrEnum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"
    EXPERT = "EXPERT"


class JobStatus(StrEnum):
    """Estado da VAGA como registro (não confundir com o pipeline, que é ApplicationStatus)."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"


class RequirementImportance(StrEnum):
    MUST_HAVE = "MUST_HAVE"
    IMPORTANT = "IMPORTANT"
    NICE_TO_HAVE = "NICE_TO_HAVE"
    UNKNOWN = "UNKNOWN"


class JobMatchStatus(StrEnum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ResumeVersionStatus(StrEnum):
    DRAFT = "DRAFT"
    READY = "READY"
    ARCHIVED = "ARCHIVED"


class ApplicationStatus(StrEnum):
    DISCOVERED = "DISCOVERED"
    QUALIFIED = "QUALIFIED"
    PREPARED = "PREPARED"
    READY = "READY"
    APPLIED = "APPLIED"
    RESPONSE = "RESPONSE"
    INTERVIEW = "INTERVIEW"
    TECHNICAL = "TECHNICAL"
    OFFER = "OFFER"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    GHOSTED = "GHOSTED"


class ApplicationEventType(StrEnum):
    CREATED = "CREATED"
    STATUS_CHANGED = "STATUS_CHANGED"
    NOTE_UPDATED = "NOTE_UPDATED"
