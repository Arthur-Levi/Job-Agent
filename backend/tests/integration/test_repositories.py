from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.domain.enums import JobStatus
from app.models import Application, CandidateProfile, Job, User
from app.repositories.application import ApplicationRepository
from app.repositories.candidate_profile import CandidateProfileRepository
from app.repositories.errors import Constraint, ConstraintViolationError
from app.repositories.job import JobRepository
from tests.integration.factories import make_application, make_job, make_profile, make_user


def test_job_list_is_newest_first_and_stable_across_pages(db_session: Session) -> None:
    user = make_user(db_session)
    base = datetime(2026, 1, 1, tzinfo=UTC)
    jobs = [
        make_job(db_session, user, title=f"J{i}", created_at=base + timedelta(days=i))
        for i in range(4)
    ]
    repo = JobRepository(db_session)

    page1 = repo.list_page(user.id, status=None, limit=2, offset=0)
    page2 = repo.list_page(user.id, status=None, limit=2, offset=2)

    assert [j.id for j in [*page1, *page2]] == [j.id for j in reversed(jobs)]


def test_job_filters_and_scoping(db_session: Session) -> None:
    user, other = make_user(db_session), make_user(db_session)
    make_job(db_session, user)
    make_job(db_session, user, status=JobStatus.CLOSED)
    make_job(db_session, other)
    repo = JobRepository(db_session)
    assert repo.count(user.id, status=None) == 2
    assert repo.count(user.id, status=JobStatus.CLOSED) == 1
    assert repo.get(user.id, make_job(db_session, other).id) is None


def test_application_get_loads_the_job_eagerly(db_session: Session) -> None:
    user = make_user(db_session)
    job = make_job(db_session, user, title="Eager")
    application = make_application(db_session, user, job)
    db_session.expire_all()
    loaded = ApplicationRepository(db_session).get(user.id, application.id, lock=True)
    assert loaded is not None
    assert loaded.job.title == "Eager"  # lazy="raise" levantaria se não fosse eager


def test_application_without_eager_job_raises(db_session: Session) -> None:
    user = make_user(db_session)
    application = make_application(db_session, user, make_job(db_session, user))
    db_session.expire_all()
    fresh = db_session.get_one(Application, application.id)
    with pytest.raises(Exception, match="lazy"):
        _ = fresh.job


def test_constraint_violations_carry_the_constraint_name(db_session: Session) -> None:
    user = make_user(db_session)
    job = make_job(db_session, user, source_url="https://x.example/1")
    application = make_application(db_session, user, job)
    make_profile(db_session, user)
    db_session.commit()

    def captured(action: object) -> str | None:
        with pytest.raises(ConstraintViolationError) as info, db_session.begin_nested():
            action()  # type: ignore[operator]
        return info.value.constraint

    jobs, apps, profiles = (
        JobRepository(db_session),
        ApplicationRepository(db_session),
        CandidateProfileRepository(db_session),
    )
    assert (
        captured(
            lambda: jobs.add(
                Job(
                    user_id=user.id,
                    title="t",
                    company="c",
                    description="d",
                    source_url="https://x.example/1",
                )
            )
        )
        == Constraint.JOB_SOURCE_URL
    )
    assert captured(lambda: jobs.delete(job)) == Constraint.JOB_HAS_APPLICATIONS
    assert (
        captured(lambda: apps.add(Application(user_id=user.id, job_id=job.id)))
        == Constraint.APPLICATION_USER_JOB
    )
    assert (
        captured(lambda: profiles.add(CandidateProfile(user_id=user.id)))
        == Constraint.CANDIDATE_PROFILE_USER
    )
    assert application.id is not None


def test_constraint_names_used_by_services_exist_in_the_schema(db_session: Session) -> None:
    rows = db_session.execute(
        text(
            "SELECT conname FROM pg_constraint UNION SELECT indexname FROM pg_indexes "
            "WHERE schemaname = 'public'"
        )
    )
    existing = {row[0] for row in rows}
    used = {v for k, v in vars(Constraint).items() if not k.startswith("_")}
    assert used <= existing, used - existing


def test_user_repository_is_case_insensitive(db_session: Session) -> None:
    from app.repositories.user import UserRepository

    db_session.add(User(name="A", email="Ana@Example.com"))
    db_session.flush()
    assert UserRepository(db_session).get_by_email("ANA@example.COM") is not None
    assert UserRepository(db_session).get_by_email("nobody@example.com") is None
