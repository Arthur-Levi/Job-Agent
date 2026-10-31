"""SEC05-FC06A: real Stripe SDK cryptographic webhook verification, isolated PG.

Opt in with SEC05_PG_INTEGRATION=1 after configuring the *disposable*
PostgreSQL at 127.0.0.1:55434/jobagent_ux, alembic revision 0006.
No Stripe network requests, no live secrets, no real charges.
"""
import hashlib
import hmac
import json
import os
import time
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

if os.getenv("SEC05_PG_INTEGRATION") != "1":
    pytest.skip("Opt-in disposable PostgreSQL only", allow_module_level=True)

stripe = pytest.importorskip("stripe")
from fastapi.testclient import TestClient
import main
from models import Session, Subscription, User, WebhookEvent


def check_target():
    url = make_url(os.environ["DATABASE_URL"])
    expected = ("postgresql+psycopg", "ux_test", "127.0.0.1", 55434, "jobagent_ux")
    actual = (url.drivername, url.username, url.host, url.port, url.database)
    assert actual == expected, "BLOCKED: wrong database target"
    with main.engine.connect() as connection:
        assert connection.execute(
            text("SELECT current_database(), current_user")
        ).one() == ("jobagent_ux", "ux_test")
        assert connection.execute(
            text("SELECT version_num FROM public.alembic_version")
        ).scalar_one() == "0006_subscription_price_guard"


def sign_event(payload, secret):
    timestamp = int(time.time())
    digest = hmac.new(
        secret.encode(), f"{timestamp}.".encode() + payload, hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v1={digest}"


def test_sec05_fc06a_real_sdk_signed_webhook(monkeypatch):
    check_target()
    run_id = uuid.uuid4().hex
    user_id = None
    email = f"sec05-fc06-{run_id}@example.invalid"
    token = "sec05-fc06-" + run_id
    cust_id = "cus_sec05_fc06_" + run_id
    sub_id = "sub_sec05_fc06_" + run_id
    secret = "whsec_fc06_local_test_" + run_id
    event_ids = [
        f"evt_sec05_fc06_active_{run_id}",
        f"evt_sec05_fc06_canceled_{run_id}",
        f"evt_sec05_fc06_reactivate_{run_id}",
    ]
    state = {"status": "active", "price": "price_jobagent_299"}
    retrieve_calls = []

    def retrieve(sid):
        assert sid == sub_id
        retrieve_calls.append(sid)
        return {
            "id": sub_id,
            "customer": cust_id,
            "status": state["status"],
            "items": {"data": [{"price": {"id": state["price"]}}]},
        }

    monkeypatch.setattr(stripe.Subscription, "retrieve", retrieve)
    monkeypatch.setattr(
        stripe.Customer, "retrieve",
        lambda customer: {"id": customer, "metadata": {"job_agent_user_id": str(user_id)}},
    )
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fc06_local_never_network")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", secret)
    monkeypatch.setenv("STRIPE_PRICE_ID", "price_jobagent_299")

    try:
        with main.SessionLocal() as db:
            user = User(email=email, password_hash="fc06-test-no-login")
            db.add(user)
            db.flush()
            user_id = user.id
            db.add(Session(
                token_hash=hashlib.sha256(token.encode()).hexdigest(),
                user_id=user_id,
                expires_at=main.now() + timedelta(hours=1),
            ))
            db.commit()

        client = TestClient(main.app)
        authorization = {"Authorization": f"Bearer {token}"}

        def premium():
            r = client.get("/api/billing/status", headers=authorization)
            assert r.status_code == 200, r.text
            return r.json()["premium_enabled"]

        def make_payload(event_id):
            return json.dumps({
                "id": event_id,
                "object": "event",
                "type": "customer.subscription.updated",
                "data": {"object": {
                    "id": sub_id, "object": "subscription",
                    "customer": cust_id,
                    "status": "active",  # deliberately stale after cancellation
                    "metadata": {"job_agent_user_id": str(user_id)},
                }},
            }, separators=(",", ":")).encode()

        def deliver(event_id, *, valid=True):
            payload = make_payload(event_id)
            header = sign_event(payload, secret)
            if not valid:
                payload += b" "
            return client.post(
                "/api/billing/webhook",
                content=payload,
                headers={"stripe-signature": header},
            )

        assert premium() is False
        invalid = deliver(event_ids[0], valid=False)
        assert invalid.status_code == 400, invalid.text
        assert premium() is False
        print("PASS: real Stripe SDK rejects altered signed payload")

        active = deliver(event_ids[0])
        assert active.status_code == 200, active.text
        assert premium() is True
        print("PASS: real SDK signature authorizes matching active Stripe subscription")

        replay = deliver(event_ids[0])
        assert replay.status_code == 200 and replay.json().get("duplicate") is True
        assert len(retrieve_calls) == 1
        print("PASS: signed replay is idempotent")

        state["status"] = "canceled"
        canceled = deliver(event_ids[1])
        assert canceled.status_code == 200, canceled.text
        assert premium() is False
        print("PASS: canceled remote subscription revokes premium")

        stale = deliver(event_ids[2])
        assert stale.status_code == 200, stale.text
        assert premium() is False
        print("PASS: valid but stale signed event cannot reactivate premium")

        with main.SessionLocal() as db:
            sub = db.get(Subscription, user_id)
            assert sub and sub.stripe_subscription_id == sub_id
            assert sub.status == "canceled"
            assert sub.stripe_price_id == "price_jobagent_299"
            assert all(db.get(WebhookEvent, item) for item in event_ids)
        print("SEC05-FC06A: REAL SDK SIGNATURE PASS")

    finally:
        check_target()
        with main.SessionLocal() as db:
            for event_id in event_ids:
                event = db.get(WebhookEvent, event_id)
                if event:
                    db.delete(event)
            if user_id is not None:
                sub = db.get(Subscription, user_id)
                if sub and sub.stripe_subscription_id == sub_id:
                    db.delete(sub)
                session = db.get(
                    Session, hashlib.sha256(token.encode()).hexdigest()
                )
                if session and session.user_id == user_id:
                    db.delete(session)
                user = db.get(User, user_id)
                if user and user.email == email:
                    db.delete(user)
            db.commit()
        print("PASS: FC06A test-only records cleaned")
