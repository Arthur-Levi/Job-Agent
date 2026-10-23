import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CandidateProfile
from app.repositories.errors import flush


class CandidateProfileRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_user_id(self, user_id: uuid.UUID) -> CandidateProfile | None:
        stmt = select(CandidateProfile).where(CandidateProfile.user_id == user_id)
        return self._session.execute(stmt).scalar_one_or_none()

    def add(self, profile: CandidateProfile) -> CandidateProfile:
        self._session.add(profile)
        flush(self._session)
        self._session.refresh(profile)
        return profile

    def update(self, profile: CandidateProfile) -> CandidateProfile:
        flush(self._session)
        self._session.refresh(profile)  # updated_at é calculado no banco
        return profile
