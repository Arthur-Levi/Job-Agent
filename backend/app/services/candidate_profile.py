from app.core.errors import ConflictError, NotFoundError
from app.models import CandidateProfile, User
from app.repositories.candidate_profile import CandidateProfileRepository
from app.repositories.errors import Constraint, ConstraintViolationError
from app.schemas.profile import ProfileCreate, ProfileUpdate
from app.services.uow import UnitOfWork, transactional


class CandidateProfileService:
    def __init__(self, profiles: CandidateProfileRepository, uow: UnitOfWork) -> None:
        self._profiles = profiles
        self._uow = uow

    def get(self, user: User) -> CandidateProfile:
        profile = self._profiles.get_by_user_id(user.id)
        if profile is None:
            raise NotFoundError("Profile not found", code="PROFILE_NOT_FOUND")
        return profile

    def create(self, user: User, data: ProfileCreate) -> CandidateProfile:
        try:
            with transactional(self._uow):
                return self._profiles.add(CandidateProfile(user_id=user.id, **data.model_dump()))
        except ConstraintViolationError as exc:
            if exc.constraint == Constraint.CANDIDATE_PROFILE_USER:
                raise ConflictError(
                    "Profile already exists", code="PROFILE_ALREADY_EXISTS"
                ) from exc
            raise

    def update(self, user: User, data: ProfileUpdate) -> CandidateProfile:
        profile = self.get(user)
        with transactional(self._uow):
            for field, value in data.model_dump(exclude_unset=True).items():
                setattr(profile, field, value)
            return self._profiles.update(profile)
