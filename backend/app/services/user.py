from app.models import User
from app.repositories.errors import ConstraintViolationError
from app.repositories.user import UserRepository
from app.services.uow import UnitOfWork, transactional


class UserService:
    """Resolve o usuário local do D1 (sem autenticação).

    Decisão: o usuário padrão é identificado por e-mail (DEFAULT_USER_EMAIL) e criado na
    primeira requisição. Quando existir auth real, só `get_current_user` (api/deps.py) muda.
    """

    def __init__(
        self, users: UserRepository, uow: UnitOfWork, *, default_email: str, default_name: str
    ) -> None:
        self._users = users
        self._uow = uow
        self._default_email = default_email
        self._default_name = default_name

    def get_or_create_default(self) -> User:
        user = self._users.get_by_email(self._default_email)
        if user is not None:
            return user
        try:
            with transactional(self._uow):
                return self._users.add(User(name=self._default_name, email=self._default_email))
        except ConstraintViolationError:
            # Outra requisição criou o usuário entre o SELECT e o INSERT.
            user = self._users.get_by_email(self._default_email)
            if user is None:
                raise
            return user
