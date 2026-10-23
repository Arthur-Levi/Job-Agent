import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from app.core.request_context import get_request_id

# Atributos padrão de LogRecord: tudo o que NÃO estiver aqui veio de `extra=`.
# color_message: ruído ANSI que o uvicorn injeta em cada registro.
_RESERVED = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime", "color_message"}


class JsonFormatter(logging.Formatter):
    """Uma linha JSON por registro: timestamp, level, logger, message, request_id."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = get_request_id()
        if request_id:
            payload["request_id"] = request_id
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload.setdefault(key, value)  # extras nunca sobrescrevem campos base
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(level: str) -> None:
    """Idempotente: substitui handlers do root e padroniza os loggers do uvicorn."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    for name in ("uvicorn", "uvicorn.error"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True

    # O access log do uvicorn é substituído pelo log de request do RequestIdMiddleware.
    access = logging.getLogger("uvicorn.access")
    access.handlers.clear()
    access.propagate = False
