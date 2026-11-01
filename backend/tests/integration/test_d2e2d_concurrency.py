"""Concurrent confirmation test. ONLY run against a disposable PostgreSQL *_test.

The migrated_engine fixture DROPS the public schema at setup. Never point
TEST_DATABASE_URL at a preserved or shared database.
"""

import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models import CareerFact, User
from app.services.career_import import confirm_import
from tests.integration.test_d2e2d_confirmation import _confirmation, _preview

SIGNING_KEY = b"synthetic-key-32chars-long-not-production"


def test_two_distinct_keys_same_user_do_not_duplicate_facts(migrated_engine: Engine) -> None:
    # The user must be committed so other DB connections can see/lock its row.
    with Session(migrated_engine) as setup:
        user = User(
            name="Concurrency Synthetic",
            email=f"race-{uuid.uuid4().hex}@example.invalid",
        )
        setup.add(user)
        setup.commit()
        user_id: UUID = user.id

    barrier = Barrier(2)

    def attempt(key: str) -> tuple[int, int]:
        with Session(migrated_engine) as db:
            user = db.get(User, user_id)
            assert user is not None
            form = _confirmation(_preview(), user, SIGNING_KEY)
            barrier.wait(timeout=10)
            result = confirm_import(
                db,
                user_id=user_id,
                confirmation=form,
                key=SIGNING_KEY,
                idempotency_key=key,
            )
            return len(result.created_fact_ids), len(result.skipped_duplicates)

    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(attempt, "race-concurrent-key-0001")
        b = pool.submit(attempt, "race-concurrent-key-0002")
        outcomes = [a.result(timeout=25), b.result(timeout=25)]

    assert sorted(outcomes) == [(0, 1), (1, 0)]
    with Session(migrated_engine) as db:
        facts = db.scalars(
            select(CareerFact).where(
                CareerFact.user_id == user_id,
                CareerFact.status == "ACTIVE",
            )
        ).all()
        assert len(facts) == 1
