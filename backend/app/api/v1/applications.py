import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import ApplicationServiceDep, CurrentUserDep
from app.core.errors import error_responses
from app.domain.enums import ApplicationStatus
from app.schemas.application import (
    ApplicationCreate,
    ApplicationDetail,
    ApplicationEventRead,
    ApplicationRead,
    ApplicationUpdate,
)
from app.schemas.common import DEFAULT_LIMIT, MAX_LIMIT, MAX_OFFSET, Page
from app.services.application import ApplicationWithEvents

router = APIRouter(prefix="/applications", tags=["applications"])


def _detail(result: ApplicationWithEvents) -> ApplicationDetail:
    base = ApplicationRead.model_validate(result.application)
    return ApplicationDetail(
        **base.model_dump(),
        events=[ApplicationEventRead.model_validate(event) for event in result.events],
    )


@router.get("", response_model=Page[ApplicationRead])
def list_applications(
    user: CurrentUserDep,
    service: ApplicationServiceDep,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    offset: Annotated[int, Query(ge=0, le=MAX_OFFSET)] = 0,
    status: Annotated[ApplicationStatus | None, Query()] = None,
    job_id: Annotated[uuid.UUID | None, Query()] = None,
) -> Page[ApplicationRead]:
    items, total = service.list(user, status=status, job_id=job_id, limit=limit, offset=offset)
    return Page[ApplicationRead](
        items=[ApplicationRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=ApplicationDetail,
    status_code=201,
    responses=error_responses(409, 422),
)
def create_application(
    data: ApplicationCreate, user: CurrentUserDep, service: ApplicationServiceDep
) -> ApplicationDetail:
    return _detail(service.create(user, data))


@router.get("/{application_id}", response_model=ApplicationDetail, responses=error_responses(404))
def get_application(
    application_id: uuid.UUID, user: CurrentUserDep, service: ApplicationServiceDep
) -> ApplicationDetail:
    return _detail(service.get(user, application_id))


@router.patch(
    "/{application_id}", response_model=ApplicationDetail, responses=error_responses(404, 409)
)
def update_application(
    application_id: uuid.UUID,
    data: ApplicationUpdate,
    user: CurrentUserDep,
    service: ApplicationServiceDep,
) -> ApplicationDetail:
    return _detail(service.update(user, application_id, data))
