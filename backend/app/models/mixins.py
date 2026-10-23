import uuid
from datetime import datetime

from sqlalchemy import DateTime, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )


class TimestampMixin:
    """Timestamps timezone-aware (timestamptz, UTC).

    updated_at usa clock_timestamp() no UPDATE (hora real da modificação, não do início da
    transação). Limitação: só vale para UPDATEs feitos via ORM; SQL cru/bulk não o atualiza.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.clock_timestamp(),
    )
