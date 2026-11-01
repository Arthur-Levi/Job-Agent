"""Isolated parser worker entrypoint; no network or application database access."""

import base64
import json
import sys

from app.core.errors import UnprocessableError
from app.services.resume_preview import MAX_FILE_BYTES, build_preview


def _resource_limits() -> None:
    if sys.platform == "linux":
        import resource

        # Linux-only. Real beta requires hardened isolated container in addition.
        memory = 768 * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
        resource.setrlimit(resource.RLIMIT_CPU, (5, 6))
        resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
        resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))


def main() -> None:
    _resource_limits()
    try:
        raw = sys.stdin.buffer.read(3_000_000)
        data = json.loads(raw)
        filename = data["filename"]
        content = base64.b64decode(data["content"], validate=True)
        if not isinstance(filename, str) or len(content) > MAX_FILE_BYTES:
            raise UnprocessableError("Arquivo não permitido", code="CV_SIZE")
        result = {"ok": True, "preview": build_preview(filename, content)}
    except UnprocessableError as exc:
        result = {"ok": False, "error": exc.code}
    except Exception:
        result = {"ok": False, "error": "CV_PARSE"}
    sys.stdout.write(json.dumps(result, separators=(",", ":"), ensure_ascii=False))


if __name__ == "__main__":
    main()
