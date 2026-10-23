from fastapi import APIRouter

from app.api.deps import CurrentUserDep, ProfileServiceDep
from app.core.errors import error_responses
from app.schemas.profile import ProfileCreate, ProfileRead, ProfileUpdate

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileRead, responses=error_responses(404))
def get_profile(user: CurrentUserDep, service: ProfileServiceDep) -> ProfileRead:
    return ProfileRead.model_validate(service.get(user))


@router.post("", response_model=ProfileRead, status_code=201, responses=error_responses(409))
def create_profile(
    data: ProfileCreate, user: CurrentUserDep, service: ProfileServiceDep
) -> ProfileRead:
    return ProfileRead.model_validate(service.create(user, data))


@router.patch("", response_model=ProfileRead, responses=error_responses(404))
def update_profile(
    data: ProfileUpdate, user: CurrentUserDep, service: ProfileServiceDep
) -> ProfileRead:
    return ProfileRead.model_validate(service.update(user, data))
