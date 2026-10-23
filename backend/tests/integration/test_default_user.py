from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import User
from app.repositories.user import UserRepository
from app.services.user import UserService
from tests.integration.factories import make_user


def service(session: Session, repo: UserRepository | None = None) -> UserService:
    return UserService(
        repo or UserRepository(session),
        session,
        default_email="local@jobagent.local",
        default_name="Local User",
    )


def user_count(session: Session) -> int:
    return int(session.execute(select(func.count()).select_from(User)).scalar_one())


def test_default_user_is_created_once(db_session: Session) -> None:
    first = service(db_session).get_or_create_default()
    second = service(db_session).get_or_create_default()
    assert first.id == second.id
    assert (first.email, first.name) == ("local@jobagent.local", "Local User")
    assert user_count(db_session) == 1


def test_existing_default_user_is_found_ignoring_case(db_session: Session) -> None:
    existing = make_user(db_session, email="LOCAL@jobagent.local")
    db_session.commit()
    assert service(db_session).get_or_create_default().id == existing.id


def test_concurrent_creation_falls_back_to_the_existing_user(db_session: Session) -> None:
    existing = make_user(db_session, email="local@jobagent.local")
    db_session.commit()

    class StaleRepository(UserRepository):
        """Primeiro SELECT "não vê" o usuário (outra requisição ainda não tinha commitado)."""

        calls = 0

        def get_by_email(self, email: str) -> User | None:
            StaleRepository.calls += 1
            return None if StaleRepository.calls == 1 else super().get_by_email(email)

    resolved = service(db_session, StaleRepository(db_session)).get_or_create_default()
    assert resolved.id == existing.id
    assert user_count(db_session) == 1
