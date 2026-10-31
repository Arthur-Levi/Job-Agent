"""SEC05-FC05: adversarial SAME-event concurrent webhook delivery on disposable PostgreSQL.

Run explicitly: SEC05_PG_INTEGRATION=1 python -m pytest tests/test_sec05_postgres_race.py -v -s
Stripe is mocked. No real payment, no original database touched.
"""
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, BrokenBarrierError
from types import SimpleNamespace

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

if os.getenv("SEC05_PG_INTEGRATION") != "1":
    pytest.skip("Opt-in PostgreSQL-only concurrency test", allow_module_level=True)

import main
from models import User, Subscription, WebhookEvent


def _verify_target():
    url = make_url(os.environ["DATABASE_URL"])
    assert (url.drivername, url.username, url.host, url.port, url.database) == (
        "postgresql+psycopg", "ux_test", "127.0.0.1", 55433, "jobagent_ux"
    ), "BLOCKED: non-disposable database"
    with main.engine.connect() as conn:
        assert conn.execute(text("SELECT current_database(), current_user")).one() == (
            "jobagent_ux", "ux_test"
        )
        assert conn.execute(
            text("SELECT version_num FROM public.alembic_version")
        ).scalar_one() == "0006_subscription_price_guard"


def test_sec05_two_simultaneous_deliveries_same_event(monkeypatch):
    """A deliberate race; FAIL reveals a concurrency gap to fix, not a production PASS."""
    from fastapi.testclient import TestClient

    _verify_target()
    run_id = uuid.uuid4().hex
    email = f"sec05-race-{run_id}@example.invalid"
    customer = f"cus_race_{run_id}"
    subscription_id = f"sub_race_{run_id}"
    event_id = f"evt_sec05_race_{run_id}"
    uid = None
    rendezvous = Barrier(2, timeout=8)

    class Webhook:
        @staticmethod
        def construct_event(payload, signature, secret):
            if signature != "mock-signed":
                raise ValueError("Bad test signature")
            return {
                "id": event_id,
                "type": "customer.subscription.updated",
                "data": {"object": {
                    "customer": customer, "id": subscription_id,
                    "metadata": {"job_agent_user_id": str(uid)},
                    "status": "active",
                }},
            }

    class SubscriptionAPI:
        @staticmethod
        def retrieve(sid):
            assert sid == subscription_id
            # Force both delivery attempts past their read-before-write stage.
            rendezvous.wait()
            return {
                "id": subscription_id,
                "customer": customer,
                "status": "active",
                "items": {"data": [{"price": {"id": "price_jobagent_299"}}]},
            }

    fake = SimpleNamespace(
        Webhook=Webhook,
        Subscription=SubscriptionAPI,
        Customer=SimpleNamespace(
            retrieve=lambda _: {"metadata": {"job_agent_user_id": str(uid)}}
        ),
        error=SimpleNamespace(SignatureVerificationError=ValueError),
    )
    monkeypatch.setattr(main, "stripe_sdk", lambda: fake)
    monkeypatch.setenv("STRIPE_PRICE_ID", "price_jobagent_299")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_mock")

    try:
        with main.SessionLocal() as db:
            u = User(email=email, password_hash="integration-test-no-login")
            db.add(u)
            db.flush()
            uid = u.id
            db.commit()

        def deliver():
            # Each worker has its own TestClient and real PostgreSQL transaction.
            with TestClient(main.app) as client:
                result = client.post(
                    "/api/billing/webhook",
                    content=event_id.encode("ascii"),
                    headers={"stripe-signature": "mock-signed"},
                )
                return result.status_code, result.json()

        with ThreadPoolExecutor(max_workers=2) as pool:
            future1 = pool.submit(deliver)
            future2 = pool.submit(deliver)
            outcome = [future1.result(timeout=15), future2.result(timeout=15)]

        print("SEC05-FC05 concurrent outcomes:", outcome)
        assert all(code == 200 for code, _ in outcome), (
            "Same signed event must be safely acknowledged or deduplicated by both workers"
        )
        with main.SessionLocal() as db:
            assert db.query(WebhookEvent).filter(WebhookEvent.id == event_id).count() == 1
            assert db.query(Subscription).filter(
                Subscription.stripe_subscription_id == subscription_id
            ).count() == 1
            subscription = db.get(Subscription, uid)
            assert subscription and subscription.stripe_price_id == "price_jobagent_299"
        print("PASS: one committed webhook, one active authorized subscription")

    finally:
        # Scoped cleanup. Only random identifiers created by this test.
        _verify_target()
        with main.SessionLocal() as db:
            evt = db.get(WebhookEvent, event_id)
            if evt:
                db.delete(evt)
            if uid is not None:
                sub = db.get(Subscription, uid)
                if sub and sub.stripe_subscription_id == subscription_id:
                    db.delete(sub)
                u = db.get(User, uid)
                if u and u.email == email:
                    db.delete(u)
            db.commit()
        print("SEC05-FC05 scoped cleanup completed")
