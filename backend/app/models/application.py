import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import ApplicationEventType, ApplicationStatus
from app.models.helpers import enum_column
from app.models.job import Job
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Application(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "applications"
    __table_args__ = (
        # Uma candidatura por vaga por usuário (evita duplicação acidental).
        UniqueConstraint("user_id", "job_id", name="uq_applications_user_id_job_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    # RESTRICT: vaga com candidaturas não pode ser apagada (preserva o histórico).
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="RESTRICT"), index=True
    )
    # RESTRICT: currículo usado numa candidatura não pode ser apagado.
    resume_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="RESTRICT"), index=True
    )
    # lazy="raise": quem precisa da vaga a carrega explicitamente (joinedload) — sem N+1 silencioso.
    job: Mapped[Job] = relationship(lazy="raise")
    status: Mapped[ApplicationStatus] = mapped_column(
        enum_column(ApplicationStatus, "status"),
        default=ApplicationStatus.DISCOVERED,
        server_default=ApplicationStatus.DISCOVERED.value,
        index=True,
    )
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)


class ApplicationEvent(UUIDPrimaryKeyMixin, Base):
    """Log append-only. UPDATE/DELETE são bloqueados por trigger (ver migration 0001)."""

    __tablename__ = "application_events"
    __table_args__ = (
        CheckConstraint(
            "event_type <> 'STATUS_CHANGED' OR to_status IS NOT NULL",
            name="status_change_has_to_status",
        ),
        Index("ix_application_events_application_id_created_at", "application_id", "created_at"),
    )

    # RESTRICT: histórico nunca é apagado em cascata.
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="RESTRICT")
    )
    event_type: Mapped[ApplicationEventType] = mapped_column(
        enum_column(ApplicationEventType, "event_type")
    )
    from_status: Mapped[ApplicationStatus | None] = mapped_column(
        enum_column(ApplicationStatus, "from_status")
    )
    to_status: Mapped[ApplicationStatus | None] = mapped_column(
        enum_column(ApplicationStatus, "to_status")
    )
    # "metadata" é reservado pelo SQLAlchemy (Base.metadata): atributo ≠ nome da coluna.
    event_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)
    # clock_timestamp(): eventos criados na mesma transação mantêm ordem estrita.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )
