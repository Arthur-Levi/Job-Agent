import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.domain.enums import ApplicationStatus
from app.models import Application, ApplicationEvent
from app.repositories.errors import flush


def _conditions(
    user_id: uuid.UUID, status: ApplicationStatus | None, job_id: uuid.UUID | None
) -> list[Any]:
    conditions: list[Any] = [Application.user_id == user_id]
    if status is not None:
        conditions.append(Application.status == status)
    if job_id is not None:
        conditions.append(Application.job_id == job_id)
    return conditions


class ApplicationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(
        self, user_id: uuid.UUID, application_id: uuid.UUID, *, lock: bool = False
    ) -> Application | None:
        """`lock=True` faz SELECT ... FOR UPDATE (só a linha da candidatura): serializa
        mudanças de status concorrentes, evitando validar contra um estado já obsoleto."""
        stmt = (
            select(Application)
            .options(joinedload(Application.job))
            .where(Application.id == application_id, Application.user_id == user_id)
        )
        if lock:
            stmt = stmt.with_for_update(of=Application)
        return self._session.execute(stmt).scalar_one_or_none()

    def list_page(
        self,
        user_id: uuid.UUID,
        *,
        status: ApplicationStatus | None,
        job_id: uuid.UUID | None,
        limit: int,
        offset: int,
    ) -> Sequence[Application]:
        stmt = (
            select(Application)
            .options(joinedload(Application.job))
            .where(*_conditions(user_id, status, job_id))
            .order_by(Application.created_at.desc(), Application.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return self._session.execute(stmt).scalars().all()

    def count(
        self, user_id: uuid.UUID, *, status: ApplicationStatus | None, job_id: uuid.UUID | None
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(Application)
            .where(*_conditions(user_id, status, job_id))
        )
        return int(self._session.execute(stmt).scalar_one())

    def add(self, application: Application) -> Application:
        self._session.add(application)
        flush(self._session)
        self._session.refresh(application, attribute_names=["created_at", "updated_at"])
        return application

    def update(self, application: Application) -> Application:
        flush(self._session)
        self._session.refresh(application, attribute_names=["updated_at"])
        return application

    def add_event(self, event: ApplicationEvent) -> ApplicationEvent:
        self._session.add(event)
        flush(self._session)
        return event

    def list_events(self, application_id: uuid.UUID) -> Sequence[ApplicationEvent]:
        stmt = (
            select(ApplicationEvent)
            .where(ApplicationEvent.application_id == application_id)
            .order_by(ApplicationEvent.created_at, ApplicationEvent.id)
        )
        return self._session.execute(stmt).scalars().all()
