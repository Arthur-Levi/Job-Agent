"""Comportamento real das constraints no PostgreSQL (rodam só com TEST_DATABASE_URL)."""

from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.enums import (
    ApplicationEventType,
    ApplicationStatus,
    JobStatus,
    RequirementImportance,
)
from app.models import (
    ApplicationEvent,
    CandidateExperience,
    CandidateProfile,
    CandidateSkill,
    Job,
    JobMatch,
    JobRequirement,
    ResumeVersion,
    User,
)
from tests.integration.factories import (
    make_application,
    make_job,
    make_profile,
    make_user,
)


def violates(session: Session, action: Callable[[], Any]) -> None:
    """A ação deve violar uma constraint. Só o SAVEPOINT da ação é desfeito."""
    with pytest.raises(IntegrityError), session.begin_nested():
        action()
        session.flush()


def count(session: Session, table: str) -> int:
    return int(session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())


# ---------- users / profile ----------


def test_user_email_is_unique_ignoring_case_but_nulls_repeat(db_session: Session) -> None:
    make_user(db_session, email="Ana@Example.com")
    make_user(db_session)
    make_user(db_session)  # vários e-mails NULL são permitidos
    violates(db_session, lambda: make_user(db_session, email="ana@example.COM"))


def test_blank_user_name_is_rejected(db_session: Session) -> None:
    violates(db_session, lambda: make_user(db_session, name="   "))


def test_only_one_profile_per_user(db_session: Session) -> None:
    user = make_user(db_session)
    make_profile(db_session, user)
    violates(db_session, lambda: make_profile(db_session, user))


def test_invalid_enum_value_is_rejected_by_check(db_session: Session) -> None:
    user = make_user(db_session)
    job = make_job(db_session, user)
    violates(
        db_session,
        lambda: db_session.execute(
            text("INSERT INTO applications (user_id, job_id, status) VALUES (:u, :j, 'BOGUS')"),
            {"u": user.id, "j": job.id},
        ),
    )


def test_user_with_profile_cannot_be_deleted(db_session: Session) -> None:
    user = make_user(db_session)
    make_profile(db_session, user)
    violates(db_session, lambda: db_session.delete(user))


# ---------- candidate children ----------


def test_skill_is_unique_per_profile_ignoring_case(db_session: Session) -> None:
    profile = make_profile(db_session, make_user(db_session))
    other = make_profile(db_session, make_user(db_session))
    db_session.add_all(
        [
            CandidateSkill(candidate_profile_id=profile.id, name="Python"),
            CandidateSkill(candidate_profile_id=other.id, name="python"),  # outro perfil: ok
        ]
    )
    db_session.flush()
    violates(
        db_session,
        lambda: db_session.add(CandidateSkill(candidate_profile_id=profile.id, name="PYTHON")),
    )


def test_deleting_profile_cascades_to_children(db_session: Session) -> None:
    profile = make_profile(db_session, make_user(db_session))
    db_session.add(CandidateSkill(candidate_profile_id=profile.id, name="SQL"))
    db_session.flush()
    db_session.execute(delete(CandidateProfile).where(CandidateProfile.id == profile.id))
    assert count(db_session, "candidate_skills") == 0


def _experience(profile: CandidateProfile, **kw: Any) -> CandidateExperience:
    base: dict[str, Any] = {
        "candidate_profile_id": profile.id,
        "company": "ACME",
        "title": "Dev",
        "description": "Did things.",
    }
    return CandidateExperience(**{**base, **kw})


def test_experience_dates_and_current_flag_are_coherent(db_session: Session) -> None:
    profile = make_profile(db_session, make_user(db_session))
    db_session.add(_experience(profile, current=True, start_date=date(2024, 1, 1)))
    db_session.add(_experience(profile, start_date=date(2020, 1, 1), end_date=date(2021, 1, 1)))
    db_session.flush()
    violates(
        db_session,
        lambda: db_session.add(_experience(profile, current=True, end_date=date(2024, 1, 1))),
    )
    violates(
        db_session,
        lambda: db_session.add(
            _experience(profile, start_date=date(2024, 5, 1), end_date=date(2024, 1, 1))
        ),
    )


# ---------- jobs ----------


def test_job_defaults_to_open_status(db_session: Session) -> None:
    job = make_job(db_session, make_user(db_session))
    db_session.refresh(job)
    assert job.status is JobStatus.OPEN


@pytest.mark.parametrize(
    "overrides",
    [
        {"salary_min": Decimal("9000"), "salary_max": Decimal("5000"), "currency": "BRL"},
        {"salary_min": Decimal("5000")},  # salário sem moeda
        {"salary_min": Decimal("-1"), "currency": "BRL"},
        {"currency": "br"},  # não é ISO 4217 em maiúsculas
    ],
)
def test_invalid_job_salary_combinations_are_rejected(
    db_session: Session, overrides: dict[str, Any]
) -> None:
    user = make_user(db_session)
    violates(db_session, lambda: make_job(db_session, user, **overrides))


def test_valid_salary_range_is_accepted(db_session: Session) -> None:
    job = make_job(
        db_session,
        make_user(db_session),
        salary_min=Decimal("5000"),
        salary_max=Decimal("8000"),
        currency="BRL",
    )
    assert job.id is not None


def test_job_source_url_is_unique_per_user_only_when_present(db_session: Session) -> None:
    user, other = make_user(db_session), make_user(db_session)
    make_job(db_session, user, source_url="https://jobs.example/1")
    make_job(db_session, other, source_url="https://jobs.example/1")  # outro usuário: ok
    make_job(db_session, user)
    make_job(db_session, user)  # sem URL: duplicatas permitidas
    violates(db_session, lambda: make_job(db_session, user, source_url="https://jobs.example/1"))


def test_job_requirement_is_unique_per_job_and_defaults_importance(db_session: Session) -> None:
    job = make_job(db_session, make_user(db_session))
    requirement = JobRequirement(job_id=job.id, name="Docker")
    db_session.add(requirement)
    db_session.flush()
    db_session.refresh(requirement)
    assert requirement.importance is RequirementImportance.UNKNOWN
    violates(db_session, lambda: db_session.add(JobRequirement(job_id=job.id, name="docker")))


def test_job_match_versions_score_and_confidence_rules(db_session: Session) -> None:
    user = make_user(db_session)
    job, profile = make_job(db_session, user), make_profile(db_session, user)

    def match(**kw: Any) -> None:
        db_session.add(JobMatch(job_id=job.id, candidate_profile_id=profile.id, **kw))

    match()
    match(analysis_version="v1")  # versões diferentes coexistem
    db_session.flush()
    violates(db_session, match)  # duplicata com analysis_version NULL
    violates(db_session, lambda: match(analysis_version="v2", score=Decimal("100.01")))
    violates(db_session, lambda: match(analysis_version="v3", confidence=Decimal("1.5")))


# ---------- applications / resumes ----------


def test_application_is_unique_per_user_and_job_and_defaults_status(db_session: Session) -> None:
    user = make_user(db_session)
    job = make_job(db_session, user)
    application = make_application(db_session, user, job)
    db_session.refresh(application)
    assert application.status is ApplicationStatus.DISCOVERED
    violates(db_session, lambda: make_application(db_session, user, job))


def test_job_with_applications_cannot_be_deleted(db_session: Session) -> None:
    user = make_user(db_session)
    job = make_job(db_session, user)
    make_application(db_session, user, job)
    violates(db_session, lambda: db_session.delete(job))


def test_deleting_job_detaches_resume_but_keeps_it(db_session: Session) -> None:
    user = make_user(db_session)
    profile = make_profile(db_session, user)
    job = make_job(db_session, user)
    resume = ResumeVersion(
        user_id=user.id, candidate_profile_id=profile.id, job_id=job.id, name="CV"
    )
    db_session.add(resume)
    db_session.flush()
    db_session.execute(delete(Job).where(Job.id == job.id))
    assert db_session.execute(select(ResumeVersion.job_id)).scalar_one() is None


def test_resume_used_by_an_application_cannot_be_deleted(db_session: Session) -> None:
    user = make_user(db_session)
    profile = make_profile(db_session, user)
    job = make_job(db_session, user)
    resume = ResumeVersion(user_id=user.id, candidate_profile_id=profile.id, name="CV")
    db_session.add(resume)
    db_session.flush()
    make_application(db_session, user, job, resume_version_id=resume.id)
    violates(db_session, lambda: db_session.delete(resume))


# ---------- application events (append-only) ----------


def _event(application_id: Any, **kw: Any) -> ApplicationEvent:
    base: dict[str, Any] = {
        "application_id": application_id,
        "event_type": ApplicationEventType.STATUS_CHANGED,
        "from_status": ApplicationStatus.DISCOVERED,
        "to_status": ApplicationStatus.QUALIFIED,
    }
    return ApplicationEvent(**{**base, **kw})


def _application_id(session: Session) -> Any:
    user = make_user(session)
    return make_application(session, user, make_job(session, user)).id


def test_status_change_event_requires_to_status(db_session: Session) -> None:
    application_id = _application_id(db_session)
    violates(db_session, lambda: db_session.add(_event(application_id, to_status=None)))


def test_events_are_immutable_and_keep_strict_order(db_session: Session) -> None:
    application_id = _application_id(db_session)
    first = _event(application_id, event_metadata={"reason": "manual"})
    second = _event(application_id, from_status=ApplicationStatus.QUALIFIED)
    db_session.add(first)
    db_session.flush()
    db_session.add(second)
    db_session.flush()
    db_session.refresh(first)
    db_session.refresh(second)
    assert first.created_at < second.created_at  # mesma transação, ordem preservada
    assert first.event_metadata == {"reason": "manual"}

    violates(
        db_session,
        lambda: db_session.execute(
            text("UPDATE application_events SET to_status = 'OFFER' WHERE id = :id"),
            {"id": first.id},
        ),
    )
    violates(
        db_session,
        lambda: db_session.execute(
            text("DELETE FROM application_events WHERE id = :id"), {"id": first.id}
        ),
    )
    assert count(db_session, "application_events") == 2


def test_application_with_history_cannot_be_deleted(db_session: Session) -> None:
    user = make_user(db_session)
    application = make_application(db_session, user, make_job(db_session, user))
    db_session.add(_event(application.id))
    db_session.flush()
    violates(db_session, lambda: db_session.delete(application))


# ---------- timestamps ----------


def test_timestamps_are_timezone_aware_and_updated_at_advances(db_session: Session) -> None:
    user = make_user(db_session)
    db_session.refresh(user)
    assert user.created_at.tzinfo is not None
    assert user.updated_at.tzinfo is not None

    user.name = "Renamed"
    db_session.flush()
    db_session.refresh(user)
    assert user.updated_at > user.created_at


def test_user_count_helper_sanity(db_session: Session) -> None:
    before = db_session.execute(select(func.count()).select_from(User)).scalar_one()
    make_user(db_session)
    after = db_session.execute(select(func.count()).select_from(User)).scalar_one()
    assert after == before + 1
