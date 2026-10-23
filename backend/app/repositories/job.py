import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.enums import JobStatus
from app.models import Job
from app.repositories.errors import flush


def _conditions(user_id: uuid.UUID, status: JobStatus | None) -> list[Any]:
    conditions: list[Any] = [Job.user_id == user_id]
    if status is not None:
        conditions.append(Job.status == status)
    return conditions


class JobRepository:
    """Leituras escopadas por user_id: recurso alheio é indistinguível de inexistente."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, user_id: uuid.UUID, job_id: uuid.UUID) -> Job | None:
        stmt = select(Job).where(Job.id == job_id, Job.user_id == user_id)
        return self._session.execute(stmt).scalar_one_or_none()

    def get_by_source_url(self, user_id: uuid.UUID, source_url: str) -> Job | None:
        stmt = select(Job).where(Job.user_id == user_id, Job.source_url == source_url)
        return self._session.execute(stmt).scalar_one_or_none()

    def list_page(
        self, user_id: uuid.UUID, *, status: JobStatus | None, limit: int, offset: int
    ) -> Sequence[Job]:
        # id desempata created_at: paginação estável.
        stmt = (
            select(Job)
            .where(*_conditions(user_id, status))
            .order_by(Job.created_at.desc(), Job.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return self._session.execute(stmt).scalars().all()

    def count(self, user_id: uuid.UUID, *, status: JobStatus | None) -> int:
        stmt = select(func.count()).select_from(Job).where(*_conditions(user_id, status))
        return int(self._session.execute(stmt).scalar_one())

    def add(self, job: Job) -> Job:
        self._session.add(job)
        flush(self._session)
        self._session.refresh(job)
        return job

    def update(self, job: Job) -> Job:
        flush(self._session)
        self._session.refresh(job)
        return job

    def delete(self, job: Job) -> None:
        self._session.delete(job)
        flush(self._session)
