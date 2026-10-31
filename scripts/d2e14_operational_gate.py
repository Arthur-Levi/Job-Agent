"""Guarded D2-E1.4 operational migration and live HTTP rate-limit proof.

Run from the isolated Job-Agent worktree using the existing backend Python venv.
Only target: Docker container jobagent-react-test-db, database jobagent_react_test,
user react_test, host 127.0.0.1:55435. Never resets or drops schema.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
PID_FILE = Path("/tmp/jobagent-d2e14-security-api.pid")
LOG_FILE = Path("/tmp/jobagent-d2e14-security-api.log")
CONTAINER = "jobagent-react-test-db"
DB_NAME = "jobagent_react_test"
DB_USER = "react_test"
DB_PORT = 55435
API_PORT = 18081
ACK = "MIGRATE_ONLY_jobagent_react_test"
API_URL = f"http://127.0.0.1:{API_PORT}"


def container_db_url() -> URL:
    data = json.loads(
        subprocess.check_output(["docker", "inspect", CONTAINER], text=True)
    )
    if len(data) != 1 or data[0]["Name"] != f"/{CONTAINER}":
        raise RuntimeError("Unexpected Docker container identity")
    item = data[0]
    if item["State"]["Status"] != "running":
        raise RuntimeError("Disposable database is not running")
    binds = item["HostConfig"]["PortBindings"]["5432/tcp"]
    if binds != [{"HostIp": "127.0.0.1", "HostPort": str(DB_PORT)}]:
        raise RuntimeError("Unexpected PostgreSQL host binding")
    env = dict(part.partition("=")[::2] for part in item["Config"]["Env"])
    if env.get("POSTGRES_DB") != DB_NAME or env.get("POSTGRES_USER") != DB_USER:
        raise RuntimeError("Disposable DB name/user do not match")
    if not env.get("POSTGRES_PASSWORD"):
        raise RuntimeError("Disposable DB password unavailable")
    return URL.create(
        "postgresql+psycopg",
        username=DB_USER,
        password=env["POSTGRES_PASSWORD"],
        host="127.0.0.1",
        port=DB_PORT,
        database=DB_NAME,
    )


def database_revision(url: URL) -> str:
    engine = create_engine(url, connect_args={"connect_timeout": 5})
    try:
        with engine.connect() as connection:
            db, user = connection.execute(
                text("SELECT current_database(), current_user")
            ).one()
            if db != DB_NAME or user != DB_USER:
                raise RuntimeError("Actual SQL connection targets a different identity")
            rev = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            if rev not in ("0002", "0003"):
                raise RuntimeError(f"Unexpected Alembic revision: {rev!r}")
            return str(rev)
    finally:
        engine.dispose()


def api_port_is_open() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex(("127.0.0.1", API_PORT)) == 0


def inspect_target() -> URL:
    url = container_db_url()
    revision = database_revision(url)
    print(
        f"TARGET VERIFIED: {DB_NAME} / {DB_USER} / "
        f"127.0.0.1:{DB_PORT} / alembic={revision}"
    )
    print(f"Port {API_PORT} currently listening: {api_port_is_open()}")
    return url



def stop_previous_api() -> None:
    """Stop only the legacy isolated server started by the earlier D2-E1 script."""
    old_pid_file = Path("/tmp/jobagent-d2e1-api.pid")
    if not old_pid_file.exists():
        if api_port_is_open():
            raise RuntimeError("Port 18081 in use by an unidentified process; refusing stop")
        print("PREVIOUS API: already stopped")
        return
    pid = int(old_pid_file.read_text().strip())
    cmd = Path(f"/proc/{pid}/cmdline").read_bytes().decode(errors="replace")
    if "uvicorn" not in cmd or "app.main:create_app" not in cmd:
        raise RuntimeError("Refusing to stop PID not identified as legacy isolated API")
    if "18081" not in cmd:
        raise RuntimeError("Refusing to stop process on unexpected port")
    actual_cwd = Path(f"/proc/{pid}/cwd").resolve()
    if actual_cwd != BACKEND.resolve():
        raise RuntimeError("Refusing to stop process outside isolated worktree")
    env = process_env(pid)
    from sqlalchemy.engine import make_url

    db = make_url(env.get("DATABASE_URL", ""))
    if (
        db.database != DB_NAME
        or db.username != DB_USER
        or db.host != "127.0.0.1"
        or db.port != DB_PORT
        or env.get("APP_ENV") != "test"
    ):
        raise RuntimeError("Refusing to stop API not bound to disposable test DB")
    os.kill(pid, signal.SIGTERM)
    for _ in range(30):
        if not api_port_is_open():
            old_pid_file.unlink(missing_ok=True)
            print(f"PREVIOUS API STOP PASS: validated isolated PID {pid}")
            return
        time.sleep(0.2)
    raise RuntimeError("Previous isolated API did not release port 18081")

def migrate(acknowledgement: str) -> None:
    url = inspect_target()
    if acknowledgement != ACK:
        raise RuntimeError(f"Migration requires exact --ack {ACK}")
    if api_port_is_open():
        raise RuntimeError(
            "Stop the old isolated API on port 18081 before migrating; "
            "do not stop any other process"
        )
    current = database_revision(url)
    if current == "0003":
        print("MIGRATION PASS: already at 0003; no changes made")
        return
    if current != "0002":
        raise RuntimeError(f"Refusing migration from {current}")
    # No DROP SCHEMA and no downgrade: Alembic upgrade 0002 -> 0003 only.
    engine = create_engine(url, connect_args={"connect_timeout": 5})
    try:
        config = Config(str(BACKEND / "alembic.ini"))
        with engine.begin() as connection:
            db = connection.execute(text("SELECT current_database()")).scalar_one()
            if db != DB_NAME:
                raise RuntimeError("Database changed during migration")
            config.attributes["connection"] = connection
            command.upgrade(config, "0003")
    finally:
        engine.dispose()
    if database_revision(url) != "0003":
        raise RuntimeError("Migration did not reach revision 0003")
    print("MIGRATION 0003 PASS: only disposable database was upgraded")


def process_env(pid: int) -> dict[str, str]:
    raw = Path(f"/proc/{pid}/environ").read_bytes()
    result: dict[str, str] = {}
    for part in raw.split(bytes([0])):
        key, sep, value = part.partition(b"=")
        if sep:
            result[key.decode()] = value.decode()
    return result


def verify_own_api(expected_url: URL) -> int:
    if not PID_FILE.exists():
        raise RuntimeError("Isolated security API PID file is missing")
    pid = int(PID_FILE.read_text().strip())
    cmdline = Path(f"/proc/{pid}/cmdline").read_bytes().decode(errors="replace")
    if "uvicorn" not in cmdline or "--no-proxy-headers" not in cmdline:
        raise RuntimeError("PID does not identify the isolated no-proxy API")
    variables = process_env(pid)
    for key, expected in (
        ("DATABASE_URL", expected_url.render_as_string(hide_password=False)),
        ("APP_ENV", "test"),
        ("AUTH_RATE_LIMIT_ENABLED", "true"),
        ("AUTH_LOGIN_IP_MAX", "8"),
        ("AUTH_LOGIN_ACCOUNT_MAX", "2"),
        ("AUTH_REGISTER_IP_MAX", "2"),
        ("AUTH_LIMIT_WINDOW_SECONDS", "60"),
        ("ALLOW_LEGACY_LOCAL_USER", "false"),
    ):
        if variables.get(key) != expected:
            raise RuntimeError(f"API process has unexpected {key} configuration")
    if not api_port_is_open():
        raise RuntimeError("Isolated security API port is not listening")
    return pid


def start() -> None:
    url = inspect_target()
    if database_revision(url) != "0003":
        raise RuntimeError("Run migrate first: revision 0003 required")
    if api_port_is_open():
        raise RuntimeError("Port 18081 is already in use; refusing to replace it")
    env = os.environ.copy()
    env.update(
        DATABASE_URL=url.render_as_string(hide_password=False),
        APP_ENV="test",
        ALLOW_LEGACY_LOCAL_USER="false",
        CORS_ORIGINS="http://localhost:5173",
        AUTH_RATE_LIMIT_ENABLED="true",
        AUTH_RATE_LIMIT_SECRET=secrets.token_urlsafe(48),
        AUTH_LOGIN_IP_MAX="8",
        AUTH_LOGIN_ACCOUNT_MAX="2",
        AUTH_REGISTER_IP_MAX="2",
        AUTH_LIMIT_WINDOW_SECONDS="60",
    )
    with LOG_FILE.open("a", encoding="utf-8") as log:
        proc = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn", "app.main:create_app",
                "--factory", "--host", "127.0.0.1", "--port",
                str(API_PORT), "--no-proxy-headers",
            ],
            env=env,
            cwd=BACKEND,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    PID_FILE.write_text(str(proc.pid), encoding="utf-8")
    for _ in range(30):
        if proc.poll() is not None:
            raise RuntimeError("Isolated security API exited; inspect private log file")
        if api_port_is_open():
            verify_own_api(url)
            print(f"ISOLATED SECURITY API START PASS: PID {proc.pid}, port {API_PORT}")
            return
        time.sleep(0.2)
    raise RuntimeError("Security API startup timed out; inspect private log file")


def post_json(path: str, payload: dict[str, object], *, spoof: str | None = None):
    headers = {"Content-Type": "application/json"}
    if spoof is not None:
        headers["X-Forwarded-For"] = spoof
    request = urllib.request.Request(
        API_URL + path,
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


def assert_status(
    label: str, result: tuple[int, dict[str, str], bytes], status: int
) -> int:
    code, headers, body = result
    if code != status:
        raise AssertionError(f"{label}: expected HTTP {status}; got HTTP {code}")
    if status == 429:
        # HTTP headers are case-insensitive; urllib may preserve "Retry-after".
        retry = next(
            (value for name, value in headers.items() if name.casefold() == "retry-after"),
            None,
        )
        if retry is None or not retry.isdecimal():
            raise AssertionError(f"{label}: missing valid Retry-After")
        if json.loads(body).get("error", {}).get("code") not in (
            "RATE_LIMITED", "HTTP_429",
        ):
            raise AssertionError(f"{label}: wrong error envelope")
        return int(retry)
    return 0



def self_test_headers() -> None:
    """No database, HTTP requests, or Docker required."""
    body = json.dumps({
        "error": {
            "code": "RATE_LIMITED",
            "message": "Too many requests. Try again later.",
        }
    }).encode()
    for header in ("Retry-After", "Retry-after", "retry-after", "RETRY-AFTER"):
        assert assert_status(
            f"case insensitive header {header}",
            (429, {header: "35"}, body),
            429,
        ) == 35
    print("HEADER CASE-INSENSITIVITY SELF-TEST PASS")

def probe() -> None:
    url = inspect_target()
    if database_revision(url) != "0003":
        raise RuntimeError("Rate-limit schema 0003 is not installed")
    pid = verify_own_api(url)
    with urllib.request.urlopen(API_URL + "/ready", timeout=5) as response:
        if response.status != 200:
            raise RuntimeError("API readiness failed")
    print(f"API PID {pid}: configured with 60-second throttling window")

    registration = "/api/v1/auth/register"
    assert_status(
        "Register attempt 1",
        post_json(registration, {"invalid": 1}, spoof="203.0.113.1"),
        422,
    )
    assert_status(
        "Register attempt 2",
        post_json(registration, {"invalid": 2}, spoof="198.51.100.99"),
        422,
    )
    register_retry = assert_status(
        "Register attempt 3",
        post_json(registration, {"invalid": 3}, spoof="192.0.2.20"),
        429,
    )
    print("REGISTER 429 PASS: malformed requests count; spoofed XFF did not evade")

    login = "/api/v1/auth/login"
    email = f"d2e14-live-{secrets.token_hex(12)}@example.com"
    for attempt in range(1, 3):
        assert_status(
            f"Login attempt {attempt}",
            post_json(login, {"email": email, "password": "invalid"}),
            401,
        )
    login_retry = assert_status(
        "Login attempt 3",
        post_json(login, {"email": email.upper(), "password": "invalid"}),
        429,
    )
    assert_status(
        "Other account is not locked",
        post_json(
            login,
            {"email": f"d2e14-other-{secrets.token_hex(12)}@example.com",
             "password": "invalid"},
        ),
        401,
    )
    print("ACCOUNT 429 PASS: normalized identity capped; unrelated account allowed")

    remaining = max(register_retry, login_retry)
    if not 1 <= remaining <= 60:
        raise AssertionError(f"Unexpected Retry-After: {remaining}")
    print(f"Waiting up to {remaining + 2} seconds for genuine window expiry...")
    time.sleep(remaining + 2)

    assert_status(
        "Registration recovery",
        post_json(registration, {"invalid": "after-expiry"}),
        422,
    )
    assert_status(
        "Login recovery",
        post_json(login, {"email": email, "password": "invalid"}),
        401,
    )
    print("WINDOW EXPIRY PASS: registration 422 and login 401 (no longer 429)")
    print("D2-E1.4 LIVE RATE-LIMIT OPERATIONAL PASS")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("inspect")
    sub.add_parser("self-test-headers")
    sub.add_parser("stop-previous-api")
    migrate_cmd = sub.add_parser("migrate")
    migrate_cmd.add_argument("--ack", required=True)
    sub.add_parser("start")
    sub.add_parser("probe")
    args = parser.parse_args()
    try:
        if args.cmd == "self-test-headers":
            self_test_headers()
        elif args.cmd == "inspect":
            inspect_target()
        elif args.cmd == "stop-previous-api":
            stop_previous_api()
        elif args.cmd == "migrate":
            migrate(args.ack)
        elif args.cmd == "start":
            start()
        elif args.cmd == "probe":
            probe()
    except Exception as exc:
        # No traceback or config dump: may include secrets.
        print(f"D2-E1.4 OPERATIONAL FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
