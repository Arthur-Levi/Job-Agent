import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.enums import (
    EmploymentType,
    JobMatchStatus,
    JobStatus,
    RequirementImportance,
    Seniority,
    WorkModel,
)
from app.models.helpers import enum_column, nonblank
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Job(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "jobs"
    __table_args__ = (
        nonblank("title"),
        nonblank("company"),
        CheckConstraint("salary_min IS NULL OR salary_min >= 0", name="salary_min_non_negative"),
        CheckConstraint("salary_max IS NULL OR salary_max >= 0", name="salary_max_non_negative"),
        CheckConstraint(
            "salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max",
            name="salary_range_ordered",
        ),
        CheckConstraint(
            "(salary_min IS NULL AND salary_max IS NULL) OR currency IS NOT NULL",
            name="salary_requires_currency",
        ),
        CheckConstraint("currency IS NULL OR currency ~ '^[A-Z]{3}$'", name="currency_iso_4217"),
        # created_at vem do mixin; índice próprio porque a listagem ordena por ele.
        Index("ix_jobs_created_at", "created_at"),
        # Mesma URL de origem não pode ser cadastrada duas vezes pelo mesmo usuário.
        Index(
            "uq_jobs_user_id_source_url",
            "user_id",
            "source_url",
            unique=True,
            postgresql_where=text("source_url IS NOT NULL"),
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    company: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(100))
    source_url: Mapped[str | None] = mapped_column(String(2048))
    location: Mapped[str | None] = mapped_column(String(200))
    work_model: Mapped[WorkModel | None] = mapped_column(enum_column(WorkModel, "work_model"))
    employment_type: Mapped[EmploymentType | None] = mapped_column(
        enum_column(EmploymentType, "employment_type")
    )
    seniority: Mapped[Seniority | None] = mapped_column(enum_column(Seniority, "seniority"))
    salary_min: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    salary_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[JobStatus] = mapped_column(
        enum_column(JobStatus, "status"),
        default=JobStatus.OPEN,
        server_default=JobStatus.OPEN.value,
        index=True,
    )


class JobRequirement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "job_requirements"
    __table_args__ = (
        nonblank("name"),
        Index("uq_job_requirements_job_lower_name", "job_id", text("lower(name)"), unique=True),
    )

    # CASCADE: requisito é parte da vaga (composição).
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    normalized_name: Mapped[str | None] = mapped_column(String(200))
    category: Mapped[str | None] = mapped_column(String(50))
    importance: Mapped[RequirementImportance] = mapped_column(
        enum_column(RequirementImportance, "importance"),
        default=RequirementImportance.UNKNOWN,
        server_default=RequirementImportance.UNKNOWN.value,
    )
    description: Mapped[str | None] = mapped_column(Text)


class JobMatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Só persistência. Nenhum algoritmo de matching existe no D1."""

    __tablename__ = "job_matches"
    __table_args__ = (
        CheckConstraint("score IS NULL OR (score >= 0 AND score <= 100)", name="score_0_100"),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="confidence_0_1"
        ),
        # Várias versões de análise coexistem (auditoria); COALESCE evita duplicata com NULL.
        Index(
            "uq_job_matches_job_profile_version",
            "job_id",
            "candidate_profile_id",
            text("coalesce(analysis_version, '')"),
            unique=True,
        ),
    )

    # CASCADE: match é dado derivado e recomputável.
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True
    )
    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    status: Mapped[JobMatchStatus] = mapped_column(
        enum_column(JobMatchStatus, "status"),
        default=JobMatchStatus.PENDING,
        server_default=JobMatchStatus.PENDING.value,
    )
    analysis_version: Mapped[str | None] = mapped_column(String(50))
