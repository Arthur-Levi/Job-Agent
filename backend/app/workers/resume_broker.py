"""Private local resume broker: Docker authority stays OUTSIDE the public API.

Protocol: 4-byte big-endian length + JSON worker input, and same framing for
bounded JSON worker output. Listen only on a UNIX-domain socket in a private
0700 directory controlled by deployment (no TCP listener).
This is a staging prototype; production approval still requires independent
deployment, scoped runtime identity, operational quotas and threat testing.
"""

import contextlib
import json
import os
import socketserver
import struct
import subprocess
import threading
from pathlib import Path
from uuid import uuid4

from app.core.errors import UnprocessableError
from app.services.resume_worker import (
    MAX_BROKER_REQUEST,
    MAX_WORKER_OUTPUT,
    _cleanup_container,
    _container_command,
    _run_bounded,
)

_BROKER_SLOTS = threading.BoundedSemaphore(2)
_BROKER_ENV = {
    "PATH": "/usr/bin:/bin",
    "HOME": "/nonexistent",
    "PYTHONIOENCODING": "utf-8",
}
_FAILURE = b'{"ok":false,"error":"CV_PARSE"}'
_BUSY = b'{"ok":false,"error":"CV_PARSER_BUSY"}'


def _receive_exact(stream: object, size: int) -> bytes:
    output = bytearray()
    while len(output) < size:
        chunk = stream.read(min(size - len(output), 65536))
        if not chunk:
            raise OSError("incomplete broker request")
        output.extend(chunk)
    return bytes(output)


def _execute(request: bytes) -> bytes:
    try:
        document = json.loads(request)
        if (
            not isinstance(document, dict)
            or not isinstance(document.get("filename"), str)
            or not isinstance(document.get("content"), str)
        ):
            return _FAILURE
    except (UnicodeDecodeError, ValueError, TypeError):
        return _FAILURE

    if not _BROKER_SLOTS.acquire(blocking=False):
        return _BUSY
    name = "jobagent-cv-" + uuid4().hex
    try:
        result = _run_bounded(_container_command(name), request, _BROKER_ENV)
        if result.returncode or len(result.stdout) > MAX_WORKER_OUTPUT:
            return _FAILURE
        try:
            payload = json.loads(result.stdout)
        except (UnicodeDecodeError, ValueError):
            return _FAILURE
        if not isinstance(payload, dict) or not isinstance(payload.get("ok"), bool):
            return _FAILURE
        return result.stdout
    except (OSError, subprocess.TimeoutExpired, UnprocessableError):
        return _FAILURE
    finally:
        _cleanup_container(name)
        _BROKER_SLOTS.release()


class BrokerHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        # No logging of request bytes: they contain personal documents.
        self.request.settimeout(12)
        try:
            raw_size = _receive_exact(self.rfile, 4)
            size = struct.unpack("!I", raw_size)[0]
            if not 0 < size <= MAX_BROKER_REQUEST:
                return
            payload = _receive_exact(self.rfile, size)
            result = _execute(payload)
            self.wfile.write(struct.pack("!I", len(result)) + result)
            self.wfile.flush()
        except (OSError, ValueError, struct.error):
            return


class ResumeBroker(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    request_queue_size = 8


def serve(socket_path: str) -> None:
    target = Path(socket_path)
    if not target.is_absolute() or len(socket_path) > 100:
        raise ValueError("Broker requires a short absolute UNIX socket path")
    # Refuse existing paths to avoid deleting or replacing arbitrary filesystem
    # entries. The directory MUST exist and must be owner-private.
    stat = target.parent.stat()
    if stat.st_mode & 0o077:
        raise ValueError("Broker directory must not be accessible by other users")
    if target.exists() or target.is_symlink():
        raise ValueError("Broker socket already exists; inspect it before starting")
    with ResumeBroker(socket_path, BrokerHandler) as server:
        os.chmod(socket_path, 0o600)
        try:
            server.serve_forever(poll_interval=0.2)
        finally:
            with contextlib.suppress(OSError):
                target.unlink()


if __name__ == "__main__":
    address = os.environ.get("RESUME_BROKER_SOCKET", "")
    if not address:
        raise SystemExit("RESUME_BROKER_SOCKET must be set explicitly")
    serve(address)
