"""CV extraction in a separate resource-limited subprocess (Linux).

This provides CPU/memory/wall-clock bounds; it is NOT a complete OS sandbox.
For external beta also use a hardened container/worker with network disabled,
non-root UID, seccomp/AppArmor, read-only filesystem, no secrets and quotas.
"""

import base64
import contextlib
import json
import os
import subprocess
import sys
from typing import Any, cast
from uuid import uuid4

from app.core.errors import ServiceUnavailableError, UnprocessableError

MAX_WORKER_SECONDS = 10
MAX_WORKER_OUTPUT = 130_000
SANDBOX_IMAGE = "job-agent-resume-parser:d2e2d1"


def _container_command(name: str) -> list[str]:
    """No host mounts, network, ambient credentials or privileged capabilities."""
    return [
        "docker",
        "run",
        "--rm",
        "--pull=never",
        "--name",
        name,
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--pids-limit=32",
        "--memory=1g",
        "--memory-swap=1g",
        "--cpus=1",
        "--user=65532:65532",
        "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=16m",
        "--env=PYTHONDONTWRITEBYTECODE=1",
        "--env=PYTHONIOENCODING=utf-8",
        "--entrypoint=python",
        "-i",
        SANDBOX_IMAGE,
        "-m",
        "app.workers.resume_parser",
    ]


def _cleanup_container(name: str) -> None:
    with contextlib.suppress(OSError, subprocess.TimeoutExpired):
        subprocess.run(
            ["docker", "rm", "-f", name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )


def parse_in_worker(filename: str, raw: bytes) -> dict[str, Any]:
    request = json.dumps({"filename": filename, "content": base64.b64encode(raw).decode()})
    # Restrict environment to prevent exposing DB credentials and tokens to parser libraries.
    safe_env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
        "PYTHONIOENCODING": "utf-8",
        "HOME": "/nonexistent",
    }
    mode = os.environ.get("RESUME_PARSER_MODE", "subprocess")
    if mode not in {"subprocess", "container"}:
        raise ServiceUnavailableError("Parser não configurado", code="CV_SANDBOX_REQUIRED")
    container_name = f"jobagent-cv-{uuid4().hex}" if mode == "container" else None
    command = (
        _container_command(container_name)
        if container_name is not None
        else [sys.executable, "-m", "app.workers.resume_parser"]
    )
    try:
        process = subprocess.run(
            command,
            input=request.encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=safe_env,
            timeout=MAX_WORKER_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        if container_name is not None:
            _cleanup_container(container_name)
        raise UnprocessableError(
            "Processamento excedeu o tempo permitido", code="CV_TIMEOUT"
        ) from None
    except OSError:
        raise ServiceUnavailableError(
            "Worker de currículo indisponível", code="CV_SANDBOX_REQUIRED"
        ) from None
    finally:
        if container_name is not None:
            _cleanup_container(container_name)
    if process.returncode != 0 and mode == "container":
        raise ServiceUnavailableError("Sandbox indisponível", code="CV_SANDBOX_REQUIRED")
    if process.returncode != 0 or len(process.stdout) > MAX_WORKER_OUTPUT:
        raise UnprocessableError("Não foi possível processar o currículo", code="CV_WORKER")
    try:
        response: dict[str, Any] = json.loads(process.stdout)
        if response.get("ok") is True and isinstance(response.get("preview"), dict):
            return cast(dict[str, Any], response["preview"])
        error = response.get("error", "CV_PARSE")
        if error not in {"CV_PARSE", "CV_SIZE", "CV_FORMAT", "CV_TEXT", "CV_PREVIEW_LIMIT"}:
            error = "CV_PARSE"
        raise UnprocessableError("Currículo inválido ou sem texto extraível", code=error)
    except (ValueError, UnicodeDecodeError, TypeError):
        raise UnprocessableError("Resposta inválida do analisador", code="CV_WORKER") from None
