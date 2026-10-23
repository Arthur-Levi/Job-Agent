import uuid
from collections.abc import Sequence

from app.core.errors import ConflictError, NotFoundError, UnprocessableError
from app.domain.enums import JobStatus
from app.domain.job_rules import validate_salary
from app.models import Job, User
from app.repositories.errors import Constraint, ConstraintViolationError
from app.repositories.job import JobRepository
from app.schemas.job import JobCreate, JobUpdate
from app.services.uow import UnitOfWork, transactional


def _check_salary(job: Job) -> None:
    error = validate_salary(job.salary_min, job.salary_max, job.currency)
    if error:
        raise UnprocessableError(error, code="JOB_INVALID_SALARY")


def _translate(exc: ConstraintViolationError) -> Exception:
    if exc.constraint == Constraint.JOB_SOURCE_URL:
        return ConflictError(
            "A job with this source_url already exists", code="JOB_SOURCE_URL_EXISTS"
        )
    if exc.constraint == Constraint.JOB_HAS_APPLICATIONS:
        return ConflictError(
            "Job has applications and cannot be deleted", code="JOB_HAS_APPLICATIONS"
        )
    return exc  # violação inesperada: não mascarar, vira 500 (e é um bug a investigar)


class JobService:
    def __init__(self, jobs: JobRepository, uow: UnitOfWork) -> None:
        self._jobs = jobs
        self._uow = uow

    def list(
        self, user: User, *, status: JobStatus | None, limit: int, offset: int
    ) -> tuple[Sequence[Job], int]:
        items = self._jobs.list_page(user.id, status=status, limit=limit, offset=offset)
        return items, self._jobs.count(user.id, status=status)

    def get(self, user: User, job_id: uuid.UUID) -> Job:
        job = self._jobs.get(user.id, job_id)
        if job is None:
            raise NotFoundError("Job not found", code="JOB_NOT_FOUND")
        return job

    def create(self, user: User, data: JobCreate) -> Job:
        job = Job(user_id=user.id, **data.model_dump())
        try:
            with transactional(self._uow):
                _check_salary(job)
                return self._jobs.add(job)
        except ConstraintViolationError as exc:
            raise _translate(exc) from exc

    def update(self, user: User, job_id: uuid.UUID, data: JobUpdate) -> Job:
        job = self.get(user, job_id)
        try:
            with transactional(self._uow):
                for field, value in data.model_dump(exclude_unset=True).items():
                    setattr(job, field, value)
                _check_salary(job)  # regra sobre o estado mesclado
                return self._jobs.update(job)
        except ConstraintViolationError as exc:
            raise _translate(exc) from exc

    def delete(self, user: User, job_id: uuid.UUID) -> None:
        job = self.get(user, job_id)
        try:
            with transactional(self._uow):
                self._jobs.delete(job)
        except ConstraintViolationError as exc:
            raise _translate(exc) from exc
