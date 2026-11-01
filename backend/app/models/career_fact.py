"""D2-E2.B: persistent confirmed import receipts and traceable career facts.

No raw resume files, extracted text or temporary previews are persisted.
The preview/confirmation API and secure preview token are NOT implemented here.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class ResumeImportRecord(UUIDPrimaryKeyMixin, Base):
    """Committed import receipt; idempotency is scoped to one user."""

    __tablename__ = "resume_import_records"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_resume_import_user_key"),
        UniqueConstraint("user_id", "id", name="uq_resume_import_user_id"),
        CheckConstraint(
            "source_format IN ('pdf','docx','txt')",
            name="resume_import_source_format",
        ),
        CheckConstraint("length(content_sha256) = 64", name="resume_import_digest_length"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    # Hash is over a canonical confirmed payload, not the original CV bytes.
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_format: Mapped[str] = mapped_column(String(8), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CareerFact(UUIDPrimaryKeyMixin, Base):
    """User-declared fact; corrections create revisions instead of overwriting."""

    __tablename__ = "career_facts"
    __table_args__ = (
        UniqueConstraint("user_id", "id", name="uq_career_facts_user_id"),
        ForeignKeyConstraint(
            ["user_id", "import_id"],
            ["resume_import_records.user_id", "resume_import_records.id"],
            name="fk_career_facts_owned_import",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["user_id", "supersedes_id"],
            ["career_facts.user_id", "career_facts.id"],
            name="fk_career_facts_owned_previous",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('ACTIVE','SUPERSEDED','REJECTED')",
            name="career_fact_status",
        ),
        CheckConstraint(
            "verification IN ('USER_DECLARED','EXTERNALLY_VERIFIED')",
            name="career_fact_verification",
        ),
        CheckConstraint(
            "source_type IN ('resume_import','user_statement','evidence','external_review')",
            name="career_fact_source_type",
        ),
        CheckConstraint(
            "char_length(btrim(subject)) > 0 AND char_length(btrim(value)) > 0",
            name="career_fact_nonblank",
        ),
        CheckConstraint(
            "supersedes_id IS NULL OR supersedes_id <> id",
            name="career_fact_no_self_supersession",
        ),
        CheckConstraint(
            "(source_type = 'resume_import' AND import_id IS NOT NULL) OR "
            "(source_type <> 'resume_import' AND import_id IS NULL)",
            name="career_fact_import_source",
        ),
        Index("ix_career_facts_user_status", "user_id", "status"),
        Index("ix_career_facts_user_subject", "user_id", "subject", "predicate"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    import_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    subject: Mapped[str] = mapped_column(String(180), nullable=False)
    predicate: Mapped[str] = mapped_column(String(80), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(300), nullable=False)
    verification: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="USER_DECLARED"
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="ACTIVE")
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
