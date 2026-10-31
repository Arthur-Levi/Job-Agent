"""SEC05-FC04 PostgreSQL API/webhook integration, disposable database ONLY.

Run separately:
  SEC05_PG_INTEGRATION=1 python -m pytest tests/test_sec05_postgres_live.py -v
Never run against production or original test databases. Stripe SDK calls are mocked.
"""
import hashlib
import os
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

if os.getenv("SEC05_PG_INTEGRATION") != "1":
    pytest.skip("Opt-in PostgreSQL financial integration test only", allow_module_level=True)

from fastapi.testclient import TestClient
from models import User, Session, Subscription, WebhookEvent
import main

_EXPECTED = (
    "postgresql+psycopg", "ux_test", "127.0.0.1", 55433, "jobagent_ux"
)


def _assert_disposable_database():
    url = make_url(os.environ["DATABASE_URL"])
    actual = (url.drivername, url.username, url.host, url.port, url.database)
    if actual != _EXPECTED:
        raise RuntimeError("SEC05 test BLOCKED: not the isolated disposable database")
    with main.engine.connect() as conn:
        assert conn.execute(
            text("SELECT current_database(), current_user")
        ).one() == ("jobagent_ux", "ux_test")
        assert conn.execute(
            text("SELECT version_num FROM public.alembic_version")
        ).scalar_one() == "0006_subscription_price_guard"
        col = conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema='public'
              AND table_name='subscriptions'
              AND column_name='stripe_price_id'
        """)).scalar_one()
        assert col == "stripe_price_id"


def test_sec05_fc04_webhook_lifecycle_postgres(monkeypatch):
    """Live PostgreSQL commit/lookup/replay/revocation; no real Stripe network."""
    from types import SimpleNamespace

    _assert_disposable_database()
    run_id = uuid.uuid4().hex
    email = f"sec05-fc04-{run_id}@example.invalid"
    raw_token = "sec05-fc04-" + run_id
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    customer = "cus_sec05_" + run_id
    subscription_id = "sub_sec05_" + run_id
    event_ids = []
    uid = None
    state = {"status": "active", "price": "price_jobagent_299"}
    retrieved = {"count": 0}
    active_event = "evt_sec05_active_" + run_id

    class Webhook:
        @staticmethod
        def construct_event(payload, signature, secret):
            if signature != "mock-valid-signature":
                raise ValueError("invalid mock signature")
            eid = payload.decode("ascii")
            return {
                "id": eid,
                "type": "customer.subscription.updated",
                "data": {"object": {
                    "customer": customer, "id": subscription_id,
                    "metadata": {"job_agent_user_id": str(uid)},
                    # Must not trust event status (can be stale).
                    "status": "active",
                }},
            }

    class SubscriptionAPI:
        @staticmethod
        def retrieve(*args):
            assert args[0] == subscription_id
            retrieved["count"] += 1
            return {
                "id": subscription_id, "customer": customer,
                "status": state["status"],
                "items": {"data": [{"price": {"id": state["price"]}}]},
            }

    stripe_mock = SimpleNamespace(
        Webhook=Webhook,
        Subscription=SubscriptionAPI,
        Customer=SimpleNamespace(
            retrieve=lambda _: {"metadata": {"job_agent_user_id": str(uid)}}
        ),
        error=SimpleNamespace(SignatureVerificationError=ValueError),
    )

    monkeypatch.setattr(main, "stripe_sdk", lambda: stripe_mock)
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_mock_local_only")
    monkeypatch.setenv("STRIPE_PRICE_ID", "price_jobagent_299")
    client = TestClient(main.app)

    def status(headers):
        response = client.get("/api/billing/status", headers=headers)
        assert response.status_code == 200, response.text
        return response.json()["premium_enabled"]

    def deliver(event_id):
        event_ids.append(event_id)
        return client.post(
            "/api/billing/webhook",
            content=event_id.encode("ascii"),
            headers={"stripe-signature": "mock-valid-signature"},
        )

    try:
        with main.SessionLocal() as db:
            user = User(email=email, password_hash="integration-test-not-a-login")
            db.add(user)
            db.flush()
            uid = user.id
            db.add(Session(
                token_hash=token_hash, user_id=uid,
                expires_at=main.now() + timedelta(hours=1),
            ))
            db.commit()

        headers = {"Authorization": f"Bearer {raw_token}"}
        assert status(headers) is False

        invalid = client.post(
            "/api/billing/webhook",
            content=("evt_sec05_invalid_" + run_id).encode(),
            headers={"stripe-signature": "bad"},
        )
        assert invalid.status_code == 400
        assert status(headers) is False

        first = deliver(active_event)
        assert first.status_code == 200, first.text
        assert status(headers) is True
        with main.SessionLocal() as db:
            sub = db.get(Subscription, uid)
            assert sub is not None
            assert sub.stripe_customer_id == customer
            assert sub.stripe_subscription_id == subscription_id
            assert sub.stripe_price_id == "price_jobagent_299"
            assert db.get(WebhookEvent, active_event) is not None
        print("PASS: signed-mock webhook persisted subscription on PostgreSQL")

        replay = deliver(active_event)
        assert replay.status_code == 200
        assert replay.json().get("duplicate") is True
        assert retrieved["count"] == 1
        print("PASS: duplicate webhook ignored after PostgreSQL commit")

        state["status"] = "canceled"
        cancel = deliver("evt_sec05_cancel_" + run_id)
        assert cancel.status_code == 200, cancel.text
        assert status(headers) is False
        print("PASS: canceled authoritative state revokes premium")

        # An out-of-order event still claims active; remote lookup is canceled.
        stale = deliver("evt_sec05_stale_" + run_id)
        assert stale.status_code == 200, stale.text
        assert status(headers) is False
        print("PASS: stale active event cannot reactivate premium")

        state["status"] = "active"
        state["price"] = "price_unrelated_product"
        wrong_price = deliver("evt_sec05_wrong_price_" + run_id)
        assert wrong_price.status_code == 200, wrong_price.text
        assert status(headers) is False
        with main.SessionLocal() as db:
            sub = db.get(Subscription, uid)
            assert sub.stripe_price_id is None
        print("PASS: price mismatch revokes premium on PostgreSQL")

    finally:
        # Remove ONLY records explicitly created with this random run_id.
        # Delete webhook IDs even if assertions fail. No broad DELETEs.
        _assert_disposable_database()
        with main.SessionLocal() as db:
            for eid in set(event_ids):
                if eid.startswith("evt_sec05_") and eid.endswith(run_id):
                    obj = db.get(WebhookEvent, eid)
                    if obj:
                        db.delete(obj)
            if uid is not None:
                subscription = db.get(Subscription, uid)
                if subscription and subscription.stripe_subscription_id == subscription_id:
                    db.delete(subscription)
                session = db.get(Session, token_hash)
                if session and session.user_id == uid:
                    db.delete(session)
                user = db.get(User, uid)
                if user and user.email == email:
                    db.delete(user)
            db.commit()
        with main.SessionLocal() as db:
            assert db.query(User).filter(User.email == email).count() == 0
            assert all(db.get(WebhookEvent, eid) is None for eid in set(event_ids))
        print("PASS: test-only data cleaned from PostgreSQL")
