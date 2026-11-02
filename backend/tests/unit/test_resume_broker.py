"""Private broker protocol tests; synthetic data only, no Docker or database."""

import json
import stat
import threading
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from app.core.errors import ServiceUnavailableError
from app.services.resume_worker import parse_in_worker
from app.workers.resume_broker import BrokerHandler, ResumeBroker, _execute


def test_broker_rejects_non_json_without_spawning() -> None:
    with patch("app.workers.resume_broker._run_bounded") as run:
        assert json.loads(_execute(b"invalid JSON"))["ok"] is False
        run.assert_not_called()


def test_broker_rejects_overload_without_spawning() -> None:
    from app.workers import resume_broker

    acquired = [resume_broker._BROKER_SLOTS.acquire(blocking=False) for _ in range(2)]
    assert acquired == [True, True]
    try:
        request = b'{"filename":"synthetic.txt","content":"YXNk"}'
        with patch("app.workers.resume_broker._run_bounded") as run:
            assert json.loads(_execute(request))["error"] == "CV_PARSER_BUSY"
            run.assert_not_called()
    finally:
        resume_broker._BROKER_SLOTS.release()
        resume_broker._BROKER_SLOTS.release()


def test_broker_executes_fixed_command_and_returns_bounded_json() -> None:
    with (
        patch("app.workers.resume_broker._run_bounded") as run,
        patch("app.workers.resume_broker._cleanup_container") as cleanup,
    ):
        run.return_value = Mock(returncode=0, stdout=b'{"ok":true,"preview":{"format":"txt"}}')
        reply = json.loads(_execute(b'{"filename":"synthetic.txt","content":"YXNk"}'))
        assert reply["preview"]["format"] == "txt"
        args = run.call_args.args[0]
        assert "--network=none" in args
        assert "app.workers.resume_parser" in args
        cleanup.assert_called_once()


def test_api_broker_unix_socket_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    directory = tmp_path / "private"
    directory.mkdir(mode=0o700)
    directory.chmod(0o700)
    address = str(directory / "resume.sock")
    with (
        ResumeBroker(address, BrokerHandler) as server,
        patch("app.workers.resume_broker._execute") as execute,
    ):
        execute.return_value = b'{"ok":true,"preview":{"format":"txt"}}'
        Path(address).chmod(0o600)
        assert stat.S_IMODE(Path(address).stat().st_mode) == 0o600
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            monkeypatch.setenv("RESUME_PARSER_MODE", "broker")
            monkeypatch.setenv("RESUME_BROKER_SOCKET", address)
            result = parse_in_worker("synthetic.txt", b"Synthetic CV")
            assert result == {"format": "txt"}
            execute.assert_called_once()
        finally:
            server.shutdown()
            thread.join(timeout=3)


def test_broker_denies_missing_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RESUME_PARSER_MODE", "broker")
    monkeypatch.setenv("RESUME_BROKER_SOCKET", "/tmp/jobagent-does-not-exist.sock")
    with pytest.raises(ServiceUnavailableError) as exc:
        parse_in_worker("synthetic.txt", b"Synthetic CV")
    assert exc.value.code == "CV_SANDBOX_REQUIRED"


