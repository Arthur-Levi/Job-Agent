"""Container runner contract: no database, Docker daemon or customer files required."""

from unittest.mock import Mock, patch

import pytest

from app.core.errors import ServiceUnavailableError, UnprocessableError
from app.services.resume_worker import SANDBOX_IMAGE, _container_command, parse_in_worker


def test_container_command_enforces_runtime_guards() -> None:
    args = _container_command("jobagent-cv-synthetic")
    assert args[:2] == ["docker", "run"]
    for guard in (
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--pids-limit=32",
        "--memory=1g",
        "--memory-swap=1g",
        "--cpus=1",
        "--user=65532:65532",
        "--pull=never",
    ):
        assert guard in args
    assert "--privileged" not in args
    assert "--volume" not in args
    assert "-v" not in args
    assert SANDBOX_IMAGE in args


def test_container_parser_fails_closed_when_runtime_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RESUME_PARSER_MODE", "container")
    with (
        patch("app.services.resume_worker.subprocess.run", side_effect=OSError("no docker")),
        pytest.raises(ServiceUnavailableError) as exc,
    ):
        parse_in_worker("sample.txt", b"Synthetic resume only")
    assert exc.value.code == "CV_SANDBOX_REQUIRED"


def test_container_parser_handles_nonzero_exit_without_leaking_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RESUME_PARSER_MODE", "container")
    with (
        patch(
            "app.services.resume_worker.subprocess.run",
            side_effect=[
                Mock(returncode=125, stdout=b"internal privileged details"),
                Mock(returncode=0),
            ],
        ),
        pytest.raises(ServiceUnavailableError) as exc,
    ):
        parse_in_worker("sample.txt", b"Synthetic resume only")
    assert exc.value.code == "CV_SANDBOX_REQUIRED"


def test_container_parser_rejects_unsupported_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RESUME_PARSER_MODE", "unexpected")
    with pytest.raises(ServiceUnavailableError) as exc:
        parse_in_worker("sample.txt", b"Synthetic resume only")
    assert exc.value.code == "CV_SANDBOX_REQUIRED"


def test_local_worker_timeout_is_mapped_to_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import subprocess

    monkeypatch.setenv("RESUME_PARSER_MODE", "subprocess")
    with (
        patch(
            "app.services.resume_worker.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="synthetic", timeout=10),
        ),
        pytest.raises(UnprocessableError) as exc,
    ):
        parse_in_worker("sample.txt", b"Synthetic resume only")
    assert exc.value.code == "CV_TIMEOUT"
