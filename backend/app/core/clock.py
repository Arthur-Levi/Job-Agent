from collections.abc import Callable
from datetime import UTC, datetime

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    """Relógio padrão (UTC, timezone-aware). Injetável nos services para testes determinísticos."""
    return datetime.now(UTC)
