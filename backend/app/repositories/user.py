from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import User
from app.repositories.errors import flush


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(func.lower(User.email) == email.lower())
        return self._session.execute(stmt).scalar_one_or_none()

    def add(self, user: User) -> User:
        self._session.add(user)
        flush(self._session)
        return user
