import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Response

from app.api.deps import CurrentUserDep, JobServiceDep
from app.core.errors import error_responses
from app.domain.enums import JobStatus
from app.schemas.common import DEFAULT_LIMIT, MAX_LIMIT, MAX_OFFSET, Page
from app.schemas.job import JobCreate, JobRead, JobUpdate

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=Page[JobRead])
def list_jobs(
    user: CurrentUserDep,
    service: JobServiceDep,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    offset: Annotated[int, Query(ge=0, le=MAX_OFFSET)] = 0,
    status: Annotated[JobStatus | None, Query()] = None,
) -> Page[JobRead]:
    items, total = service.list(user, status=status, limit=limit, offset=offset)
    return Page[JobRead](
        items=[JobRead.model_validate(job) for job in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=JobRead, status_code=201, responses=error_responses(409))
def create_job(data: JobCreate, user: CurrentUserDep, service: JobServiceDep) -> JobRead:
    return JobRead.model_validate(service.create(user, data))


@router.get("/{job_id}", response_model=JobRead, responses=error_responses(404))
def get_job(job_id: uuid.UUID, user: CurrentUserDep, service: JobServiceDep) -> JobRead:
    return JobRead.model_validate(service.get(user, job_id))


@router.patch("/{job_id}", response_model=JobRead, responses=error_responses(404, 409))
def update_job(
    job_id: uuid.UUID, data: JobUpdate, user: CurrentUserDep, service: JobServiceDep
) -> JobRead:
    return JobRead.model_validate(service.update(user, job_id, data))


@router.delete("/{job_id}", status_code=204, responses=error_responses(404, 409))
def delete_job(job_id: uuid.UUID, user: CurrentUserDep, service: JobServiceDep) -> Response:
    service.delete(user, job_id)
    return Response(status_code=204)
