"""D2-E2.B: additive candidate import receipts and career fact history.

Revision ID: 0005
Revises: 0004

NO deletion of existing user data. Only apply on separately gated disposable DB.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "resume_import_records",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("source_format", sa.String(8), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source_format IN ('pdf','docx','txt')",
            name=op.f("ck_resume_import_records_resume_import_source_format"),
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name=op.f("ck_resume_import_records_resume_import_digest_length"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name=op.f("fk_resume_import_records_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_resume_import_records")),
        sa.UniqueConstraint(
            "user_id", "idempotency_key", name="uq_resume_import_user_key"
        ),
        sa.UniqueConstraint("user_id", "id", name="uq_resume_import_user_id"),
    )
    op.create_index(
        op.f("ix_resume_import_records_user_id"),
        "resume_import_records", ["user_id"],
    )
    op.create_table(
        "career_facts",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("import_id", sa.Uuid(), nullable=True),
        sa.Column("subject", sa.String(180), nullable=False),
        sa.Column("predicate", sa.String(80), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("source_reference", sa.String(300), nullable=False),
        sa.Column("verification", sa.String(32), server_default="USER_DECLARED", nullable=False),
        sa.Column("status", sa.String(16), server_default="ACTIVE", nullable=False),
        sa.Column("supersedes_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE','SUPERSEDED','REJECTED')",
            name=op.f("ck_career_facts_career_fact_status"),
        ),
        sa.CheckConstraint(
            "verification IN ('USER_DECLARED','EXTERNALLY_VERIFIED')",
            name=op.f("ck_career_facts_career_fact_verification"),
        ),
        sa.CheckConstraint(
            "source_type IN ('resume_import','user_statement','evidence','external_review')",
            name=op.f("ck_career_facts_career_fact_source_type"),
        ),
        sa.CheckConstraint(
            "char_length(btrim(subject)) > 0 AND char_length(btrim(value)) > 0",
            name=op.f("ck_career_facts_career_fact_nonblank"),
        ),
        sa.CheckConstraint(
            "supersedes_id IS NULL OR supersedes_id <> id",
            name=op.f("ck_career_facts_career_fact_no_self_supersession"),
        ),
        sa.CheckConstraint(
            "(source_type = 'resume_import' AND import_id IS NOT NULL) OR "
            "(source_type <> 'resume_import' AND import_id IS NULL)",
            name=op.f("ck_career_facts_career_fact_import_source"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name=op.f("fk_career_facts_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id", "import_id"],
            ["resume_import_records.user_id", "resume_import_records.id"],
            name="fk_career_facts_owned_import",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id", "supersedes_id"],
            ["career_facts.user_id", "career_facts.id"],
            name="fk_career_facts_owned_previous",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_career_facts")),
        sa.UniqueConstraint("user_id", "id", name="uq_career_facts_user_id"),
    )
    op.create_index(op.f("ix_career_facts_user_id"), "career_facts", ["user_id"])
    op.create_index(
        "ix_career_facts_user_status", "career_facts", ["user_id", "status"]
    )
    op.create_index(
        "ix_career_facts_user_subject",
        "career_facts", ["user_id", "subject", "predicate"],
    )


def downgrade() -> None:
    # ONLY in ephemeral CI DB; never on Codespaces preserved DB.
    op.drop_index("ix_career_facts_user_subject", table_name="career_facts")
    op.drop_index("ix_career_facts_user_status", table_name="career_facts")
    op.drop_index(op.f("ix_career_facts_user_id"), table_name="career_facts")
    op.drop_table("career_facts")
    op.drop_index(op.f("ix_resume_import_records_user_id"), table_name="resume_import_records")
    op.drop_table("resume_import_records")
