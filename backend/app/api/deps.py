from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.clock import Clock, utc_now
from app.core.config import Settings
from app.db.session import Database
from app.models import User
from app.repositories.application import ApplicationRepository
from app.repositories.candidate_profile import CandidateProfileRepository
from app.repositories.job import JobRepository
from app.repositories.user import UserRepository
from app.services import auth
from app.services.application import ApplicationService
from app.services.candidate_profile import CandidateProfileService
from app.services.job import JobService
from app.services.readiness import ReadinessService
from app.services.user import UserService


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_database(request: Request) -> Database:
    database: Database = request.app.state.database
    return database


def get_session(database: Annotated[Database, Depends(get_database)]) -> Iterator[Session]:
    """Uma sessão por request. Rollback em erro e close sempre; commit é do service."""
    session = database.new_session()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[Session, Depends(get_session)]


def get_clock() -> Clock:
    return utc_now


ClockDep = Annotated[Clock, Depends(get_clock)]


# --- services (composição: repositories + UnitOfWork = a própria Session) ---


def get_readiness_service(session: SessionDep) -> ReadinessService:
    return ReadinessService(session)


def get_user_service(session: SessionDep, settings: SettingsDep) -> UserService:
    return UserService(
        UserRepository(session),
        session,
        default_email=settings.default_user_email,
        default_name=settings.default_user_name,
    )


def get_profile_service(session: SessionDep) -> CandidateProfileService:
    return CandidateProfileService(CandidateProfileRepository(session), session)


def get_job_service(session: SessionDep) -> JobService:
    return JobService(JobRepository(session), session)


def get_application_service(session: SessionDep, clock: ClockDep) -> ApplicationService:
    return ApplicationService(
        ApplicationRepository(session), JobRepository(session), session, clock
    )


def get_current_user(
    session: SessionDep,
    settings: SettingsDep,
    service: Annotated[UserService, Depends(get_user_service)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """Resolve identity from a revocable bearer token; no shared-user fallback by default."""
    if authorization:
        scheme, sep, token = authorization.partition(" ")
        if sep and scheme.lower() == "bearer":
            user = auth.current(session, token)
            if user is not None:
                return user
        raise HTTPException(401, "Sessão inválida")
    if settings.allow_legacy_local_user and not settings.is_production:
        return service.get_or_create_default()
    raise HTTPException(401, "Autenticação necessária")


ReadinessServiceDep = Annotated[ReadinessService, Depends(get_readiness_service)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]
ProfileServiceDep = Annotated[CandidateProfileService, Depends(get_profile_service)]
JobServiceDep = Annotated[JobService, Depends(get_job_service)]
ApplicationServiceDep = Annotated[ApplicationService, Depends(get_application_service)]
