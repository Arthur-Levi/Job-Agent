from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import Application, CandidateProfile, Job, User

_counter = 0


def _next() -> int:
    global _counter
    _counter += 1
    return _counter


def make_user(session: Session, **overrides: Any) -> User:
    user = User(**{"name": f"User {_next()}", **overrides})
    session.add(user)
    session.flush()
    return user


def make_profile(session: Session, user: User, **overrides: Any) -> CandidateProfile:
    profile = CandidateProfile(user_id=user.id, **overrides)
    session.add(profile)
    session.flush()
    return profile


def make_job(session: Session, user: User, **overrides: Any) -> Job:
    job = Job(
        **{
            "user_id": user.id,
            "title": f"Backend Developer {_next()}",
            "company": "ACME",
            "description": "Build APIs.",
            "published_at": datetime.now(UTC),
            **overrides,
        }
    )
    session.add(job)
    session.flush()
    return job


def make_application(session: Session, user: User, job: Job, **overrides: Any) -> Application:
    application = Application(user_id=user.id, job_id=job.id, **overrides)
    session.add(application)
    session.flush()
    return application
