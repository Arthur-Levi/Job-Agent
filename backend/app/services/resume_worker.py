"""CV extraction in a separate resource-limited subprocess (Linux).

This provides CPU/memory/wall-clock bounds; it is NOT a complete OS sandbox.
For external beta also use a hardened container/worker with network disabled,
non-root UID, seccomp/AppArmor, read-only filesystem, no secrets and quotas.
"""

import base64
import json
import os
import subprocess
import sys
from typing import Any

from app.core.errors import UnprocessableError

MAX_WORKER_SECONDS = 10
MAX_WORKER_OUTPUT = 130_000


def parse_in_worker(filename: str, raw: bytes) -> dict[str, Any]:
    request = json.dumps({"filename": filename, "content": base64.b64encode(raw).decode()})
    # Restrict environment to prevent exposing DB credentials and tokens to parser libraries.
    safe_env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
        "PYTHONIOENCODING": "utf-8",
        "HOME": "/nonexistent",
    }
    try:
        process = subprocess.run(
            [sys.executable, "-m", "app.workers.resume_parser"],
            input=request.encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=safe_env,
            timeout=MAX_WORKER_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise UnprocessableError(
            "Processamento excedeu o tempo permitido", code="CV_TIMEOUT"
        ) from None
    if process.returncode != 0 or len(process.stdout) > MAX_WORKER_OUTPUT:
        raise UnprocessableError("Não foi possível processar o currículo", code="CV_WORKER")
    try:
        response: dict[str, Any] = json.loads(process.stdout)
        if response.get("ok") is True and isinstance(response.get("preview"), dict):
            return response["preview"]
        error = response.get("error", "CV_PARSE")
        if error not in {"CV_PARSE", "CV_SIZE", "CV_FORMAT", "CV_TEXT", "CV_PREVIEW_LIMIT"}:
            error = "CV_PARSE"
        raise UnprocessableError("Currículo inválido ou sem texto extraível", code=error)
    except (ValueError, UnicodeDecodeError, TypeError):
        raise UnprocessableError("Resposta inválida do analisador", code="CV_WORKER") from None
