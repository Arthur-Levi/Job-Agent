from datetime import datetime

from sqlalchemy import DateTime, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.helpers import nonblank
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Representa apenas ownership (sem autenticação no D1)."""

    __tablename__ = "users"
    __table_args__ = (
        nonblank("name"),
        # e-mail único sem diferenciar maiúsculas; NULLs múltiplos são permitidos.
        Index("uq_users_email_lower", text("lower(email)"), unique=True),
    )

    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320))
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
