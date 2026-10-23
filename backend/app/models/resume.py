import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.enums import ResumeVersionStatus
from app.models.helpers import enum_column, nonblank
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ResumeVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Só persistência. Nenhuma geração de currículo existe no D1."""

    __tablename__ = "resume_versions"
    __table_args__ = (nonblank("name"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    # RESTRICT: currículos gerados não somem ao apagar o perfil.
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="RESTRICT"), index=True
    )
    # SET NULL: o currículo sobrevive à vaga (só desvincula).
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    content: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ResumeVersionStatus] = mapped_column(
        enum_column(ResumeVersionStatus, "status"),
        default=ResumeVersionStatus.DRAFT,
        server_default=ResumeVersionStatus.DRAFT.value,
    )
