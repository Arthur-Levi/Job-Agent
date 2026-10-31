"""D2-E1.5.1 guarded additive Alembic migration, isolated Codespaces DB ONLY.

This script never drops schema and never runs the destructive pytest fixtures.
It intentionally refuses to migrate until the previously launched API is
verified and stopped. Run with the backend venv from the isolated worktree.
"""
from __future__ import annotations

import argparse
import os
import signal
import sys
import time

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

import d2e14_operational_gate as prior

ACK = "UPGRADE_0004_ONLY_jobagent_react_test"


def checked_revision() -> tuple[object, str]:
    url = prior.container_db_url()
    engine = create_engine(url, connect_args={"connect_timeout": 5})
    try:
        with engine.connect() as con:
            name, user, revision = con.execute(
                text(
                    "SELECT current_database(), current_user, "
                    "(SELECT version_num FROM alembic_version)"
                )
            ).one()
            if name != prior.DB_NAME or user != prior.DB_USER:
                raise RuntimeError("SQL-connected database identity mismatch")
            if revision not in {"0003", "0004"}:
                raise RuntimeError("Expected exactly revision 0003 or 0004")
    finally:
        engine.dispose()
    print(f"GUARDED TARGET: {name} / {user} / 127.0.0.1:55435 / {revision}")
    return url, str(revision)


def stop_verified_api() -> None:
    url, _ = checked_revision()
    if not prior.api_port_is_open():
        print("ISOLATED API: already stopped")
        return
    pid = prior.verify_own_api(url)
    # Protect against killing a reused PID or different process.
    if not os.path.exists(f"/proc/{pid}"):
        raise RuntimeError("Verified API PID disappeared; re-inspect")
    os.kill(pid, signal.SIGTERM)
    for _ in range(40):
        if not prior.api_port_is_open():
            print(f"VERIFIED ISOLATED API STOP PASS: {pid}")
            return
        time.sleep(0.25)
    raise RuntimeError("API did not release port 18081; migration aborted")


def migrate(ack: str) -> None:
    url, current = checked_revision()
    if ack != ACK:
        raise RuntimeError("Missing exact disposable migration acknowledgement")
    if prior.api_port_is_open():
        raise RuntimeError("Isolated API port 18081 must be stopped first")
    if current == "0004":
        print("D2-E1.5.1 MIGRATION PASS: already 0004, no changes")
        return
    if current != "0003":
        raise RuntimeError("Refusing unexpected migration path")

    engine = create_engine(url, connect_args={"connect_timeout": 5})
    try:
        config = Config(str(prior.BACKEND / "alembic.ini"))
        with engine.begin() as con:
            name, user = con.execute(
                text("SELECT current_database(), current_user")
            ).one()
            if name != prior.DB_NAME or user != prior.DB_USER:
                raise RuntimeError("Database identity changed before migration")
            config.attributes["connection"] = con
            command.upgrade(config, "0004")
    finally:
        engine.dispose()
    _, after = checked_revision()
    if after != "0004":
        raise RuntimeError("Migration did not reach 0004")
    print("D2-E1.5.1 MIGRATION 0004 PASS: additive upgrade, disposable DB only")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("inspect")
    sub.add_parser("stop-verified-api")
    command_parser = sub.add_parser("migrate")
    command_parser.add_argument("--ack", required=True)
    args = parser.parse_args()
    try:
        if args.action == "inspect":
            checked_revision()
            print(f"Port 18081 listening: {prior.api_port_is_open()}")
        elif args.action == "stop-verified-api":
            stop_verified_api()
        elif args.action == "migrate":
            migrate(args.ack)
    except Exception as exc:
        print(f"D2-E1.5.1 GATE FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
