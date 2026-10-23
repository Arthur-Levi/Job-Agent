import json
import logging

from app.core.logging import JsonFormatter
from app.core.request_context import reset_request_id, set_request_id


def _record(**extra: object) -> logging.LogRecord:
    record = logging.LogRecord("app.test", logging.INFO, __file__, 1, "hello %s", ("world",), None)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_json_formatter_emits_required_fields() -> None:
    payload = json.loads(JsonFormatter().format(_record()))
    assert payload["message"] == "hello world"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "app.test"
    assert "timestamp" in payload
    assert "request_id" not in payload


def test_json_formatter_includes_request_id_when_available() -> None:
    token = set_request_id("req-12345678")
    try:
        payload = json.loads(JsonFormatter().format(_record()))
    finally:
        reset_request_id(token)
    assert payload["request_id"] == "req-12345678"


def test_json_formatter_includes_extra_fields() -> None:
    payload = json.loads(JsonFormatter().format(_record(status_code=200)))
    assert payload["status_code"] == 200


def test_extra_fields_cannot_override_core_fields() -> None:
    payload = json.loads(JsonFormatter().format(_record(level="HACKED", logger="spoofed")))
    assert payload["level"] == "INFO"
    assert payload["logger"] == "app.test"
