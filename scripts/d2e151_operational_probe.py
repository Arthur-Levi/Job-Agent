"""D2-E1.5.1 live PostgreSQL + FastAPI ASGI identity lifecycle acceptance.

Only disposable jobagent_react_test at 127.0.0.1:55435. Do not run pytest:
its integration fixture DROPS the public schema. This harness instead wraps
synthetic writes in one outer transaction and ROLLS BACK after the probe.
No API listener, external email, schema operations, or plaintext-token logs.
"""
from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

import d2e151_migration_gate as gate

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

ACK = "PROBE_ONLY_jobagent_react_test_REV0004"


def run(ack: str) -> None:
    if ack != ACK:
        raise RuntimeError("Missing explicit disposable-only probe acknowledgement")
    url, revision = gate.checked_revision()
    if revision != "0004":
        raise RuntimeError("Refusing: migration 0004 has not been confirmed")
    if gate.prior.api_port_is_open():
        raise RuntimeError(
            "Refusing: port 18081 still serves the old API. Stop the verified isolated API."
        )

    # Imports only after the destination and schema were independently checked.
    from fastapi.testclient import TestClient

    from app.api.deps import get_session
    from app.core.config import Settings
    from app.main import create_app
    from app.models import AuthActionToken
    from app.services.auth import digest, now_utc
    from app.services.email_delivery import MemoryMailer

    from datetime import timedelta

    engine = create_engine(url, connect_args={"connect_timeout": 5})
    email = f"d2e151-ops-{secrets.token_hex(15)}@example.com"
    missing = f"d2e151-missing-{secrets.token_hex(15)}@example.com"
    old_password = "D2E151-ops-Old-Password-Only-123!"
    new_password = "D2E151-ops-New-Password-Only-789!"
    try:
        with engine.connect() as connection:
            outer = connection.begin()
            session = Session(bind=connection, join_transaction_mode="create_savepoint")
            try:
                actual = connection.execute(
                    text("SELECT current_database(), current_user")
                ).one()
                if actual != (gate.prior.DB_NAME, gate.prior.DB_USER):
                    raise RuntimeError("Connected database identity changed")
                settings = Settings(
                    _env_file=None,
                    app_env="test",
                    database_url=url.render_as_string(hide_password=False),
                    allow_legacy_local_user=False,
                    registration_privacy_enabled=True,
                    identity_lifecycle_enabled=True,
                    email_delivery_mode="memory",
                    public_frontend_url="http://localhost:5173",
                    auth_rate_limit_enabled=False,
                    log_level="WARNING",
                )
                app = create_app(settings)
                app.dependency_overrides[get_session] = lambda: session
                with TestClient(app) as client:
                    mailer = app.state.mailer
                    if not isinstance(mailer, MemoryMailer):
                        raise RuntimeError("Isolated in-memory mailer unavailable")

                    def post(route: str, body: dict[str, str]):
                        return client.post("/api/v1/auth/" + route, json=body)

                    def token() -> str:
                        messages = mailer.messages
                        if not messages or "#token=" not in messages[-1].link:
                            raise AssertionError("Memory outbox did not receive token link")
                        return messages[-1].link.partition("#token=")[2]

                    registration = post(
                        "register",
                        {"name": "D2E151 Synthetic",
                         "email": email, "password": old_password},
                    )
                    assert registration.status_code == 202
                    assert "email" not in registration.text.lower()
                    assert registration.headers["Cache-Control"] == "no-store"
                    initial_token = token()
                    assert session.get(AuthActionToken, digest(initial_token)) is not None
                    print("REGISTER / HASHED OUTBOX TOKEN PASS")

                    before = post("login", {"email": email, "password": old_password})
                    assert before.status_code == 401
                    assert post("verify-email", {"token": initial_token}).status_code == 204
                    assert post("verify-email", {"token": initial_token}).status_code == 400
                    print("UNVERIFIED LOGIN / ONE-USE VERIFICATION PASS")

                    tokens: list[str] = []
                    for _ in range(2):
                        signed = post("login", {"email": email, "password": old_password})
                        assert signed.status_code == 200
                        tokens.append(signed.json()["access_token"])
                    before_sent = len(mailer.messages)
                    unknown_response = post("request-password-reset", {"email": missing})
                    known_response = post("request-password-reset", {"email": email})
                    assert unknown_response.status_code == known_response.status_code == 202
                    assert unknown_response.json() == known_response.json()
                    assert len(mailer.messages) == before_sent + 1
                    recovery_token = token()
                    print("GENERIC ACCOUNT RECOVERY / TWO SESSIONS PASS")

                    reset = post(
                        "reset-password",
                        {"token": recovery_token, "new_password": new_password},
                    )
                    assert reset.status_code == 204
                    assert post(
                        "reset-password",
                        {"token": recovery_token, "new_password": new_password},
                    ).status_code == 400
                    for bearer in tokens:
                        r = client.get(
                            "/api/v1/auth/me",
                            headers={"Authorization": f"Bearer {bearer}"},
                        )
                        assert r.status_code == 401
                    assert post(
                        "login", {"email": email, "password": old_password}
                    ).status_code == 401
                    assert post(
                        "login", {"email": email, "password": new_password}
                    ).status_code == 200
                    print("RESET REPLAY / TWO SESSION REVOCATIONS / NEW PASSWORD PASS")

                    # New verification is ineligible for an already verified account.
                    assert post("request-verification", {"email": email}).status_code == 202
                    assert len(mailer.messages) == before_sent + 1

                    # New reset token, artificially expire only synthetic token
                    # inside the transaction; no server clocks or live rows altered.
                    assert post("request-password-reset", {"email": email}).status_code == 202
                    expired_token = token()
                    record = session.get(AuthActionToken, digest(expired_token))
                    assert record is not None
                    record.expires_at = now_utc() - timedelta(seconds=2)
                    session.flush()
                    assert post(
                        "reset-password",
                        {"token": expired_token, "new_password": old_password},
                    ).status_code == 400
                    print("EXPIRED TOKEN / INELIGIBLE VERIFICATION PASS")

                # Explicitly roll back all synthetic identities, sessions and
                # token records. Never commit outer transaction to the database.
            finally:
                session.close()
                outer.rollback()

        # Independent connection proves no synthetic user survived.
        with engine.connect() as verify:
            remaining = verify.execute(
                text("SELECT count(*) FROM users WHERE email IN (:a, :b)"),
                {"a": email, "b": missing},
            ).scalar_one()
            if remaining != 0:
                raise RuntimeError("Synthetic test accounts unexpectedly persisted")
        print("ROLLBACK VERIFIED: zero synthetic test accounts persisted")
        print("D2-E1.5.1 OPERATIONAL IDENTITY LIFECYCLE PASS")
    finally:
        engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ack", required=True)
    args = parser.parse_args()
    try:
        run(args.ack)
    except Exception as exc:
        # Avoid printing session tokens, connection URLs or email addresses.
        print(
            f"D2-E1.5.1 OPERATIONAL FAIL: {type(exc).__name__} "
            "(inspect test configuration and private logs; no secrets printed)",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
