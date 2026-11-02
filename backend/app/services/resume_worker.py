"""CV extraction in a separate resource-limited subprocess (Linux).

This provides CPU/memory/wall-clock bounds; it is NOT a complete OS sandbox.
For external beta also use a hardened container/worker with network disabled,
non-root UID, seccomp/AppArmor, read-only filesystem, no secrets and quotas.
"""

import base64
import contextlib
import json
import os
import selectors
import socket
import struct
import subprocess
import sys
import threading
import time
from typing import Any, cast
from uuid import uuid4

from app.core.errors import ServiceUnavailableError, UnprocessableError

MAX_WORKER_SECONDS = 10
MAX_WORKER_OUTPUT = 130_000
SANDBOX_IMAGE = "job-agent-resume-parser:d2e2d1"
MAX_BROKER_REQUEST = 3_000_000
# Per-API-process admission control, not a distributed quota.
_PARSER_SLOTS = threading.BoundedSemaphore(value=2)


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


def _run_bounded(
    command: list[str], request: bytes, env: dict[str, str]
) -> subprocess.CompletedProcess[bytes]:
    """Read child output incrementally; abort before retaining > MAX_WORKER_OUTPUT.

    A separate writer prevents deadlocks when the parser responds before consuming
    stdin. One monotonic deadline bounds upload, execution and output collection.
    """
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=env,
    )
    assert process.stdin is not None
    assert process.stdout is not None
    deadline = time.monotonic() + MAX_WORKER_SECONDS

    def send() -> None:
        try:
            assert process.stdin is not None
            process.stdin.write(request)
            process.stdin.close()
        except (BrokenPipeError, OSError, ValueError):
            pass

    writer = threading.Thread(target=send, name="cv-parser-input", daemon=True)
    writer.start()
    output = bytearray()
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(command, MAX_WORKER_SECONDS)
                events = selector.select(remaining)
                if not events:
                    raise subprocess.TimeoutExpired(command, MAX_WORKER_SECONDS)
                for key, _ in events:
                    chunk = os.read(key.fd, min(65536, MAX_WORKER_OUTPUT + 1 - len(output)))
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    output.extend(chunk)
                    if len(output) > MAX_WORKER_OUTPUT:
                        raise UnprocessableError(
                            "Resposta do parser excedeu o limite", code="CV_WORKER"
                        )
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(command, MAX_WORKER_SECONDS)
        returncode = process.wait(timeout=remaining)
        return subprocess.CompletedProcess(command, returncode, bytes(output))
    except (subprocess.TimeoutExpired, UnprocessableError):
        process.kill()
        process.wait()
        raise
    finally:
        process.stdout.close()
        writer.join(timeout=1)


def _read_exact(sock: socket.socket, length: int) -> bytes:
    data = bytearray()
    while len(data) < length:
        chunk = sock.recv(min(65536, length - len(data)))
        if not chunk:
            raise OSError("Broker disconnected")
        data.extend(chunk)
    return bytes(data)


def _broker_request(request: bytes) -> subprocess.CompletedProcess[bytes]:
    """Private UNIX socket protocol; API never accesses container runtime.

    This is intentionally local-only and does not enable production preview.
    Socket filesystem permissions are part of the broker deployment contract.
    """
    path = os.environ.get("RESUME_BROKER_SOCKET", "")
    if not path.startswith("/") or len(path) > 100 or len(request) > MAX_BROKER_REQUEST:
        raise ServiceUnavailableError(
            "Executor isolado não configurado", code="CV_SANDBOX_REQUIRED"
        )
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(MAX_WORKER_SECONDS + 3)
            sock.connect(path)
            sock.sendall(struct.pack("!I", len(request)) + request)
            size = struct.unpack("!I", _read_exact(sock, 4))[0]
            if size > MAX_WORKER_OUTPUT:
                raise OSError("Oversized broker response")
            result = _read_exact(sock, size)
        return subprocess.CompletedProcess(["resume-broker"], 0, result)
    except (OSError, ValueError, struct.error):
        raise ServiceUnavailableError(
            "Executor isolado indisponível", code="CV_SANDBOX_REQUIRED"
        ) from None


def parse_in_worker(filename: str, raw: bytes) -> dict[str, Any]:
    # Reject bursts before allocating encoded requests or starting a parser.
    if not _PARSER_SLOTS.acquire(blocking=False):
        raise ServiceUnavailableError(
            "Limite temporário de processamento de currículos", code="CV_PARSER_BUSY"
        )
    try:
        return _parse_with_slot(filename, raw)
    finally:
        _PARSER_SLOTS.release()


def _parse_with_slot(filename: str, raw: bytes) -> dict[str, Any]:
    request = json.dumps({"filename": filename, "content": base64.b64encode(raw).decode()})
    # Restrict environment to prevent exposing DB credentials and tokens to parser libraries.
    safe_env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
        "PYTHONIOENCODING": "utf-8",
        "HOME": "/nonexistent",
    }
    mode = os.environ.get("RESUME_PARSER_MODE", "subprocess")
    if mode not in {"subprocess", "container", "broker"}:
        raise ServiceUnavailableError("Parser não configurado", code="CV_SANDBOX_REQUIRED")
    container_name = f"jobagent-cv-{uuid4().hex}" if mode == "container" else None
    command = (
        _container_command(container_name)
        if container_name is not None
        else [sys.executable, "-m", "app.workers.resume_parser"]
    )
    try:
        process = (
            _broker_request(request.encode())
            if mode == "broker"
            else _run_bounded(command, request.encode(), safe_env)
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
