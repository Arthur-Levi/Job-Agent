import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from app.core.clock import Clock, utc_now
from app.core.errors import ConflictError, NotFoundError, UnprocessableError
from app.domain.application_status import InvalidStatusTransition, validate_transition
from app.domain.enums import ApplicationEventType, ApplicationStatus
from app.models import Application, ApplicationEvent, User
from app.repositories.application import ApplicationRepository
from app.repositories.errors import Constraint, ConstraintViolationError
from app.repositories.job import JobRepository
from app.schemas.application import ApplicationCreate, ApplicationUpdate
from app.services.uow import UnitOfWork, transactional


@dataclass(frozen=True)
class ApplicationWithEvents:
    application: Application
    events: Sequence[ApplicationEvent]


class ApplicationService:
    def __init__(
        self,
        applications: ApplicationRepository,
        jobs: JobRepository,
        uow: UnitOfWork,
        clock: Clock = utc_now,
    ) -> None:
        self._applications = applications
        self._jobs = jobs
        self._uow = uow
        self._clock = clock

    def list(
        self,
        user: User,
        *,
        status: ApplicationStatus | None,
        job_id: uuid.UUID | None,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[Application], int]:
        items = self._applications.list_page(
            user.id, status=status, job_id=job_id, limit=limit, offset=offset
        )
        return items, self._applications.count(user.id, status=status, job_id=job_id)

    def get(self, user: User, application_id: uuid.UUID) -> ApplicationWithEvents:
        return self._detail(user, application_id)

    def create(self, user: User, data: ApplicationCreate) -> ApplicationWithEvents:
        job = self._jobs.get(user.id, data.job_id)
        if job is None:
            raise UnprocessableError("Referenced job does not exist", code="INVALID_JOB_REFERENCE")
        application = Application(
            user_id=user.id, job=job, status=ApplicationStatus.DISCOVERED, notes=data.notes
        )
        try:
            with transactional(self._uow):
                self._applications.add(application)
                # Candidatura e evento CREATED na MESMA transação.
                self._applications.add_event(
                    ApplicationEvent(
                        application_id=application.id,
                        event_type=ApplicationEventType.CREATED,
                        to_status=application.status,
                    )
                )
        except ConstraintViolationError as exc:
            if exc.constraint == Constraint.APPLICATION_USER_JOB:
                raise ConflictError(
                    "An application for this job already exists",
                    code="APPLICATION_ALREADY_EXISTS",
                ) from exc
            raise
        return self._detail(user, application.id)

    def update(
        self, user: User, application_id: uuid.UUID, data: ApplicationUpdate
    ) -> ApplicationWithEvents:
        with transactional(self._uow):
            # FOR UPDATE: duas mudanças concorrentes não validam contra o mesmo estado antigo.
            application = self._applications.get(user.id, application_id, lock=True)
            if application is None:
                raise NotFoundError("Application not found", code="APPLICATION_NOT_FOUND")

            if "notes" in data.model_fields_set:
                application.notes = data.notes
            if "applied_at" in data.model_fields_set:
                application.applied_at = data.applied_at

            if data.status is not None and data.status != application.status:
                self._change_status(application, data.status, force=data.force)

            self._applications.update(application)
        return self._detail(user, application_id)

    def _change_status(
        self, application: Application, target: ApplicationStatus, *, force: bool
    ) -> None:
        current = application.status
        try:
            validate_transition(current, target, force=force)
        except InvalidStatusTransition as exc:
            raise ConflictError(
                str(exc),
                code="INVALID_STATUS_TRANSITION",
                details={
                    "from": exc.current.value,
                    "to": exc.target.value,
                    "allowed": exc.allowed,
                },
            ) from exc

        application.status = target
        if target is ApplicationStatus.APPLIED and application.applied_at is None:
            application.applied_at = self._clock()
        metadata: dict[str, Any] | None = {"forced": True} if force else None
        # Mudança de status e evento: mesma transação (commit único no `transactional` do caller).
        self._applications.add_event(
            ApplicationEvent(
                application_id=application.id,
                event_type=ApplicationEventType.STATUS_CHANGED,
                from_status=current,
                to_status=target,
                event_metadata=metadata,
            )
        )

    def _detail(self, user: User, application_id: uuid.UUID) -> ApplicationWithEvents:
        application = self._applications.get(user.id, application_id)
        if application is None:
            raise NotFoundError("Application not found", code="APPLICATION_NOT_FOUND")
        return ApplicationWithEvents(
            application=application, events=self._applications.list_events(application_id)
        )
