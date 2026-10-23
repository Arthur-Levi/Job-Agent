import uuid
from datetime import date

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.enums import Seniority, SkillProficiency, WorkModel
from app.models.helpers import enum_column, nonblank
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class CandidateProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "candidate_profiles"
    __table_args__ = (UniqueConstraint("user_id", name="uq_candidate_profiles_user_id"),)

    # RESTRICT: apagar um usuário nunca apaga perfil/histórico por tabela.
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    headline: Mapped[str | None] = mapped_column(String(200))
    summary: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str | None] = mapped_column(String(100))
    desired_work_model: Mapped[WorkModel | None] = mapped_column(
        enum_column(WorkModel, "desired_work_model")
    )
    desired_seniority: Mapped[Seniority | None] = mapped_column(
        enum_column(Seniority, "desired_seniority")
    )


class CandidateSkill(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "candidate_skills"
    __table_args__ = (
        nonblank("name"),
        # Duplicata "óbvia" = mesmo nome ignorando caixa, dentro do mesmo perfil.
        Index(
            "uq_candidate_skills_profile_lower_name",
            "candidate_profile_id",
            text("lower(name)"),
            unique=True,
        ),
    )

    # CASCADE: skill não existe sem o perfil (composição).
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    normalized_name: Mapped[str | None] = mapped_column(String(100))
    proficiency: Mapped[SkillProficiency | None] = mapped_column(
        enum_column(SkillProficiency, "proficiency")
    )


class CandidateProject(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "candidate_projects"
    __table_args__ = (nonblank("name"),)

    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(2048))


class CandidateExperience(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "candidate_experiences"
    __table_args__ = (
        nonblank("company"),
        nonblank("title"),
        CheckConstraint('NOT "current" OR end_date IS NULL', name="current_has_no_end_date"),
        CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR end_date >= start_date",
            name="end_not_before_start",
        ),
    )

    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True
    )
    company: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    current: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))


class CandidateEducation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "candidate_educations"
    __table_args__ = (
        nonblank("institution"),
        nonblank("course"),
        CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR end_date >= start_date",
            name="end_not_before_start",
        ),
    )

    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True
    )
    institution: Mapped[str] = mapped_column(String(200))
    course: Mapped[str] = mapped_column(String(200))
    degree: Mapped[str | None] = mapped_column(String(100))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
