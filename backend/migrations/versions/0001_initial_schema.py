"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-06 20:21:33.916805
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("char_length(btrim(name)) > 0", name=op.f("ck_users_nonblank_name")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(
        "uq_users_email_lower", "users", [sa.literal_column("lower(email)")], unique=True
    )
    op.create_table(
        "candidate_profiles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("headline", sa.String(length=200), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column(
            "desired_work_model",
            sa.Enum(
                "REMOTE",
                "HYBRID",
                "ONSITE",
                name="desired_work_model",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=True,
        ),
        sa.Column(
            "desired_seniority",
            sa.Enum(
                "INTERN",
                "JUNIOR",
                "MID",
                "SENIOR",
                "LEAD",
                name="desired_seniority",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=True,
        ),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_candidate_profiles_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_candidate_profiles")),
        sa.UniqueConstraint("user_id", name="uq_candidate_profiles_user_id"),
    )
    op.create_table(
        "jobs",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("company", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("location", sa.String(length=200), nullable=True),
        sa.Column(
            "work_model",
            sa.Enum(
                "REMOTE",
                "HYBRID",
                "ONSITE",
                name="work_model",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=True,
        ),
        sa.Column(
            "employment_type",
            sa.Enum(
                "FULL_TIME",
                "PART_TIME",
                "CONTRACT",
                "INTERNSHIP",
                "TEMPORARY",
                "FREELANCE",
                name="employment_type",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=True,
        ),
        sa.Column(
            "seniority",
            sa.Enum(
                "INTERN",
                "JUNIOR",
                "MID",
                "SENIOR",
                "LEAD",
                name="seniority",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=True,
        ),
        sa.Column("salary_min", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("salary_max", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "OPEN",
                "CLOSED",
                "ARCHIVED",
                name="status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            server_default="OPEN",
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "currency IS NULL OR currency ~ '^[A-Z]{3}$'", name=op.f("ck_jobs_currency_iso_4217")
        ),
        sa.CheckConstraint(
            "(salary_min IS NULL AND salary_max IS NULL) OR currency IS NOT NULL",
            name=op.f("ck_jobs_salary_requires_currency"),
        ),
        sa.CheckConstraint(
            "char_length(btrim(company)) > 0", name=op.f("ck_jobs_nonblank_company")
        ),
        sa.CheckConstraint("char_length(btrim(title)) > 0", name=op.f("ck_jobs_nonblank_title")),
        sa.CheckConstraint(
            "salary_max IS NULL OR salary_max >= 0", name=op.f("ck_jobs_salary_max_non_negative")
        ),
        sa.CheckConstraint(
            "salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max",
            name=op.f("ck_jobs_salary_range_ordered"),
        ),
        sa.CheckConstraint(
            "salary_min IS NULL OR salary_min >= 0", name=op.f("ck_jobs_salary_min_non_negative")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_jobs_user_id_users"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
    )
    op.create_index("ix_jobs_created_at", "jobs", ["created_at"], unique=False)
    op.create_index(op.f("ix_jobs_status"), "jobs", ["status"], unique=False)
    op.create_index(op.f("ix_jobs_user_id"), "jobs", ["user_id"], unique=False)
    op.create_index(
        "uq_jobs_user_id_source_url",
        "jobs",
        ["user_id", "source_url"],
        unique=True,
        postgresql_where=sa.text("source_url IS NOT NULL"),
    )
    op.create_table(
        "candidate_educations",
        sa.Column("candidate_profile_id", sa.Uuid(), nullable=False),
        sa.Column("institution", sa.String(length=200), nullable=False),
        sa.Column("course", sa.String(length=200), nullable=False),
        sa.Column("degree", sa.String(length=100), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "char_length(btrim(course)) > 0", name=op.f("ck_candidate_educations_nonblank_course")
        ),
        sa.CheckConstraint(
            "char_length(btrim(institution)) > 0",
            name=op.f("ck_candidate_educations_nonblank_institution"),
        ),
        sa.CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR end_date >= start_date",
            name=op.f("ck_candidate_educations_end_not_before_start"),
        ),
        sa.ForeignKeyConstraint(
            ["candidate_profile_id"],
            ["candidate_profiles.id"],
            name=op.f("fk_candidate_educations_candidate_profile_id_candidate_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_candidate_educations")),
    )
    op.create_index(
        op.f("ix_candidate_educations_candidate_profile_id"),
        "candidate_educations",
        ["candidate_profile_id"],
        unique=False,
    )
    op.create_table(
        "candidate_experiences",
        sa.Column("candidate_profile_id", sa.Uuid(), nullable=False),
        sa.Column("company", sa.String(length=200), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("current", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            'NOT "current" OR end_date IS NULL',
            name=op.f("ck_candidate_experiences_current_has_no_end_date"),
        ),
        sa.CheckConstraint(
            "char_length(btrim(company)) > 0",
            name=op.f("ck_candidate_experiences_nonblank_company"),
        ),
        sa.CheckConstraint(
            "char_length(btrim(title)) > 0", name=op.f("ck_candidate_experiences_nonblank_title")
        ),
        sa.CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR end_date >= start_date",
            name=op.f("ck_candidate_experiences_end_not_before_start"),
        ),
        sa.ForeignKeyConstraint(
            ["candidate_profile_id"],
            ["candidate_profiles.id"],
            name=op.f("fk_candidate_experiences_candidate_profile_id_candidate_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_candidate_experiences")),
    )
    op.create_index(
        op.f("ix_candidate_experiences_candidate_profile_id"),
        "candidate_experiences",
        ["candidate_profile_id"],
        unique=False,
    )
    op.create_table(
        "candidate_projects",
        sa.Column("candidate_profile_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "char_length(btrim(name)) > 0", name=op.f("ck_candidate_projects_nonblank_name")
        ),
        sa.ForeignKeyConstraint(
            ["candidate_profile_id"],
            ["candidate_profiles.id"],
            name=op.f("fk_candidate_projects_candidate_profile_id_candidate_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_candidate_projects")),
    )
    op.create_index(
        op.f("ix_candidate_projects_candidate_profile_id"),
        "candidate_projects",
        ["candidate_profile_id"],
        unique=False,
    )
    op.create_table(
        "candidate_skills",
        sa.Column("candidate_profile_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("normalized_name", sa.String(length=100), nullable=True),
        sa.Column(
            "proficiency",
            sa.Enum(
                "BEGINNER",
                "INTERMEDIATE",
                "ADVANCED",
                "EXPERT",
                name="proficiency",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=True,
        ),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "char_length(btrim(name)) > 0", name=op.f("ck_candidate_skills_nonblank_name")
        ),
        sa.ForeignKeyConstraint(
            ["candidate_profile_id"],
            ["candidate_profiles.id"],
            name=op.f("fk_candidate_skills_candidate_profile_id_candidate_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_candidate_skills")),
    )
    op.create_index(
        op.f("ix_candidate_skills_candidate_profile_id"),
        "candidate_skills",
        ["candidate_profile_id"],
        unique=False,
    )
    op.create_index(
        "uq_candidate_skills_profile_lower_name",
        "candidate_skills",
        ["candidate_profile_id", sa.literal_column("lower(name)")],
        unique=True,
    )
    op.create_table(
        "job_matches",
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_profile_id", sa.Uuid(), nullable=False),
        sa.Column("score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("confidence", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "COMPLETED",
                "FAILED",
                name="status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("analysis_version", sa.String(length=50), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name=op.f("ck_job_matches_confidence_0_1"),
        ),
        sa.CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 100)",
            name=op.f("ck_job_matches_score_0_100"),
        ),
        sa.ForeignKeyConstraint(
            ["candidate_profile_id"],
            ["candidate_profiles.id"],
            name=op.f("fk_job_matches_candidate_profile_id_candidate_profiles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], name=op.f("fk_job_matches_job_id_jobs"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_matches")),
    )
    op.create_index(
        op.f("ix_job_matches_candidate_profile_id"),
        "job_matches",
        ["candidate_profile_id"],
        unique=False,
    )
    op.create_index(
        "uq_job_matches_job_profile_version",
        "job_matches",
        ["job_id", "candidate_profile_id", sa.literal_column("coalesce(analysis_version, '')")],
        unique=True,
    )
    op.create_table(
        "job_requirements",
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("normalized_name", sa.String(length=200), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column(
            "importance",
            sa.Enum(
                "MUST_HAVE",
                "IMPORTANT",
                "NICE_TO_HAVE",
                "UNKNOWN",
                name="importance",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            server_default="UNKNOWN",
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "char_length(btrim(name)) > 0", name=op.f("ck_job_requirements_nonblank_name")
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            name=op.f("fk_job_requirements_job_id_jobs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_requirements")),
    )
    op.create_index(
        op.f("ix_job_requirements_job_id"), "job_requirements", ["job_id"], unique=False
    )
    op.create_index(
        "uq_job_requirements_job_lower_name",
        "job_requirements",
        ["job_id", sa.literal_column("lower(name)")],
        unique=True,
    )
    op.create_table(
        "resume_versions",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_profile_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT",
                "READY",
                "ARCHIVED",
                name="status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            server_default="DRAFT",
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "char_length(btrim(name)) > 0", name=op.f("ck_resume_versions_nonblank_name")
        ),
        sa.ForeignKeyConstraint(
            ["candidate_profile_id"],
            ["candidate_profiles.id"],
            name=op.f("fk_resume_versions_candidate_profile_id_candidate_profiles"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            name=op.f("fk_resume_versions_job_id_jobs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_resume_versions_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_resume_versions")),
    )
    op.create_index(
        op.f("ix_resume_versions_candidate_profile_id"),
        "resume_versions",
        ["candidate_profile_id"],
        unique=False,
    )
    op.create_index(op.f("ix_resume_versions_job_id"), "resume_versions", ["job_id"], unique=False)
    op.create_index(
        op.f("ix_resume_versions_user_id"), "resume_versions", ["user_id"], unique=False
    )
    op.create_table(
        "applications",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("resume_version_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "DISCOVERED",
                "QUALIFIED",
                "PREPARED",
                "READY",
                "APPLIED",
                "RESPONSE",
                "INTERVIEW",
                "TECHNICAL",
                "OFFER",
                "REJECTED",
                "WITHDRAWN",
                "GHOSTED",
                name="status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            server_default="DISCOVERED",
            nullable=False,
        ),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], name=op.f("fk_applications_job_id_jobs"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["resume_version_id"],
            ["resume_versions.id"],
            name=op.f("fk_applications_resume_version_id_resume_versions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_applications_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_applications")),
        sa.UniqueConstraint("user_id", "job_id", name="uq_applications_user_id_job_id"),
    )
    op.create_index(op.f("ix_applications_job_id"), "applications", ["job_id"], unique=False)
    op.create_index(
        op.f("ix_applications_resume_version_id"),
        "applications",
        ["resume_version_id"],
        unique=False,
    )
    op.create_index(op.f("ix_applications_status"), "applications", ["status"], unique=False)
    op.create_index(op.f("ix_applications_user_id"), "applications", ["user_id"], unique=False)
    op.create_table(
        "application_events",
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column(
            "event_type",
            sa.Enum(
                "CREATED",
                "STATUS_CHANGED",
                "NOTE_UPDATED",
                name="event_type",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column(
            "from_status",
            sa.Enum(
                "DISCOVERED",
                "QUALIFIED",
                "PREPARED",
                "READY",
                "APPLIED",
                "RESPONSE",
                "INTERVIEW",
                "TECHNICAL",
                "OFFER",
                "REJECTED",
                "WITHDRAWN",
                "GHOSTED",
                name="from_status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=True,
        ),
        sa.Column(
            "to_status",
            sa.Enum(
                "DISCOVERED",
                "QUALIFIED",
                "PREPARED",
                "READY",
                "APPLIED",
                "RESPONSE",
                "INTERVIEW",
                "TECHNICAL",
                "OFFER",
                "REJECTED",
                "WITHDRAWN",
                "GHOSTED",
                name="to_status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=True,
        ),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint(
            "event_type <> 'STATUS_CHANGED' OR to_status IS NOT NULL",
            name=op.f("ck_application_events_status_change_has_to_status"),
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_application_events_application_id_applications"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_application_events")),
    )
    op.create_index(
        "ix_application_events_application_id_created_at",
        "application_events",
        ["application_id", "created_at"],
        unique=False,
    )

    # application_events é append-only: UPDATE/DELETE levantam restrict_violation (SQLSTATE 23001,
    # que o driver expõe como IntegrityError). TRUNCATE não é bloqueado (reset de dev/testes).
    op.execute(
        """
        CREATE FUNCTION prevent_application_event_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'application_events is append-only (% blocked)', TG_OP
                USING ERRCODE = 'restrict_violation';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_application_events_append_only
        BEFORE UPDATE OR DELETE ON application_events
        FOR EACH ROW EXECUTE FUNCTION prevent_application_event_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_application_events_append_only ON application_events")
    op.execute("DROP FUNCTION IF EXISTS prevent_application_event_mutation()")
    op.drop_index(
        "ix_application_events_application_id_created_at", table_name="application_events"
    )
    op.drop_table("application_events")
    op.drop_index(op.f("ix_applications_user_id"), table_name="applications")
    op.drop_index(op.f("ix_applications_status"), table_name="applications")
    op.drop_index(op.f("ix_applications_resume_version_id"), table_name="applications")
    op.drop_index(op.f("ix_applications_job_id"), table_name="applications")
    op.drop_table("applications")
    op.drop_index(op.f("ix_resume_versions_user_id"), table_name="resume_versions")
    op.drop_index(op.f("ix_resume_versions_job_id"), table_name="resume_versions")
    op.drop_index(op.f("ix_resume_versions_candidate_profile_id"), table_name="resume_versions")
    op.drop_table("resume_versions")
    op.drop_index("uq_job_requirements_job_lower_name", table_name="job_requirements")
    op.drop_index(op.f("ix_job_requirements_job_id"), table_name="job_requirements")
    op.drop_table("job_requirements")
    op.drop_index("uq_job_matches_job_profile_version", table_name="job_matches")
    op.drop_index(op.f("ix_job_matches_candidate_profile_id"), table_name="job_matches")
    op.drop_table("job_matches")
    op.drop_index("uq_candidate_skills_profile_lower_name", table_name="candidate_skills")
    op.drop_index(op.f("ix_candidate_skills_candidate_profile_id"), table_name="candidate_skills")
    op.drop_table("candidate_skills")
    op.drop_index(
        op.f("ix_candidate_projects_candidate_profile_id"), table_name="candidate_projects"
    )
    op.drop_table("candidate_projects")
    op.drop_index(
        op.f("ix_candidate_experiences_candidate_profile_id"), table_name="candidate_experiences"
    )
    op.drop_table("candidate_experiences")
    op.drop_index(
        op.f("ix_candidate_educations_candidate_profile_id"), table_name="candidate_educations"
    )
    op.drop_table("candidate_educations")
    op.drop_index(
        "uq_jobs_user_id_source_url",
        table_name="jobs",
        postgresql_where=sa.text("source_url IS NOT NULL"),
    )
    op.drop_index(op.f("ix_jobs_user_id"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_status"), table_name="jobs")
    op.drop_index("ix_jobs_created_at", table_name="jobs")
    op.drop_table("jobs")
    op.drop_table("candidate_profiles")
    op.drop_index("uq_users_email_lower", table_name="users")
    op.drop_table("users")
