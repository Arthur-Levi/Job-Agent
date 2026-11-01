"""Ephemeral CI smoke test for the resume parser container. Synthetic input only.

Run after building backend/Dockerfile.resume-parser and pip install -e backend.
No PostgreSQL or customer files are accessed.
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.resume_worker import SANDBOX_IMAGE, _container_command, parse_in_worker  # noqa: E402


def main() -> None:
    os.environ["RESUME_PARSER_MODE"] = "container"
    sample = (
        "Candidato Sintetico\n"
        "Experiencia profissional\n"
        "Empresa Exemplo | Analista de Dados | 2023-2024\n"
        "Dashboards sinteticos de Excel e Power BI.\n"
    )
    preview = parse_in_worker("synthetic.txt", sample.encode("utf-8"))
    assert preview["format"] == "txt"
    assert preview["items"], "Synthetic resume has no extracted items"

    probe = r"""
import os
import socket
assert os.getuid() != 0
assert 'DATABASE_URL' not in os.environ
assert 'RESEND_API_KEY' not in os.environ
try:
    with open('/opt/parser/should-not-write.txt', 'w') as target:
        target.write('test')
except OSError:
    pass
else:
    raise AssertionError('root filesystem is writable')
try:
    with socket.create_connection(('1.1.1.1', 443), timeout=2):
        pass
except OSError:
    pass
else:
    raise AssertionError('outbound network was available')
print('sandbox-runtime-smoke-pass')
"""
    name = "jobagent-cv-smoke-" + __import__("uuid").uuid4().hex
    cmd = _container_command(name)
    cmd[-2:] = ["-c", probe]
    result = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=15, check=False, env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
    )
    if result.returncode != 0 or b"sandbox-runtime-smoke-pass" not in result.stdout:
        raise RuntimeError("Sandbox smoke failed (container execution or denied capabilities)")
    print("D2-E2.D.1-B sandbox synthetic smoke PASS")


if __name__ == "__main__":
    main()
