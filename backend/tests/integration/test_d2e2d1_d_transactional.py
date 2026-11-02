"""Acceptance: real multi-connection PostgreSQL only; public schema reset in CI.

Never run on a preserved Codespaces PostgreSQL database.
"""

import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID

import pytest
from sqlalchemy import delete, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.errors import ConflictError
from app.models import CandidateProfile, CareerFact, ResumeImportRecord, User
from app.services.career_facts import correct_fact, list_facts, master_profile
from app.services.career_import import confirm_import
from tests.integration.test_d2e2d_confirmation import _confirmation, _preview

SIGNING_KEY = b"synthetic-key-32chars-long-not-production"


def _committed_user(engine: Engine) -> UUID:
    with Session(engine) as db:
        user = User(
            name="Synthetic Transaction Acceptance",
            email=f"transaction-{uuid.uuid4().hex}@example.invalid",
        )
        db.add(user)
        db.commit()
        return user.id


def _cleanup(engine: Engine, user_id: UUID) -> None:
    with Session(engine) as db:
        db.execute(delete(CareerFact).where(CareerFact.user_id == user_id))
        db.execute(delete(ResumeImportRecord).where(ResumeImportRecord.user_id == user_id))
        db.execute(delete(CandidateProfile).where(CandidateProfile.user_id == user_id))
        db.execute(delete(User).where(User.id == user_id))
        db.commit()


def test_import_survives_new_database_session(migrated_engine: Engine) -> None:
    user_id = _committed_user(migrated_engine)
    try:
        with Session(migrated_engine) as db:
            user = db.get(User, user_id)
            assert user is not None
            result = confirm_import(
                db,
                user_id=user_id,
                confirmation=_confirmation(_preview(), user, SIGNING_KEY),
                key=SIGNING_KEY,
                idempotency_key="persisted-new-session-0001",
            )
            import_id = result.import_id
            fact_id = result.created_fact_ids[0]

        with Session(migrated_engine) as db:
            receipt = db.get(ResumeImportRecord, import_id)
            fact = db.get(CareerFact, fact_id)
            assert receipt is not None
            assert receipt.user_id == user_id
            assert fact is not None
            assert fact.user_id == user_id
            assert fact.verification == "USER_DECLARED"
            assert len(master_profile(db, user_id)["items"]) == 1
    finally:
        _cleanup(migrated_engine, user_id)


def test_failed_fact_insert_rolls_back_receipt_and_profile(migrated_engine: Engine) -> None:
    user_id = _committed_user(migrated_engine)

    def abort_synthetic_fact(_mapper: object, _connection: object, target: CareerFact) -> None:
        if target.user_id == user_id:
            raise RuntimeError("synthetic injected failure")

    event.listen(CareerFact, "before_insert", abort_synthetic_fact)
    try:
        with Session(migrated_engine) as db:
            user = db.get(User, user_id)
            assert user is not None
            with pytest.raises(RuntimeError, match="synthetic injected failure"):
                confirm_import(
                    db,
                    user_id=user_id,
                    confirmation=_confirmation(_preview(), user, SIGNING_KEY),
                    key=SIGNING_KEY,
                    idempotency_key="rollback-injected-failure-0001",
                )
    finally:
        event.remove(CareerFact, "before_insert", abort_synthetic_fact)
    try:
        with Session(migrated_engine) as verify:
            assert (
                verify.scalar(
                    select(ResumeImportRecord).where(ResumeImportRecord.user_id == user_id)
                )
                is None
            )
            assert (
                verify.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user_id))
                is None
            )
            assert list_facts(verify, user_id, include_history=True) == []
    finally:
        _cleanup(migrated_engine, user_id)


def test_correction_racing_reimport_never_resurrects_superseded_fact(
    migrated_engine: Engine,
) -> None:
    user_id = _committed_user(migrated_engine)
    try:
        with Session(migrated_engine) as db:
            user = db.get(User, user_id)
            assert user is not None
            initial_preview = _preview()
            initial = confirm_import(
                db,
                user_id=user_id,
                confirmation=_confirmation(initial_preview, user, SIGNING_KEY),
                key=SIGNING_KEY,
                idempotency_key="race-correction-initial-0001",
            )
            original_id = initial.created_fact_ids[0]

        barrier = Barrier(2)

        def correction() -> str:
            with Session(migrated_engine) as db:
                barrier.wait(timeout=10)
                return str(
                    correct_fact(
                        db,
                        user_id,
                        original_id,
                        "Descricao corrigida manualmente",
                        "Revisao sintetica",
                    ).id
                )

        def reimport() -> str:
            with Session(migrated_engine) as db:
                user = db.get(User, user_id)
                assert user is not None
                form = _confirmation(initial_preview, user, SIGNING_KEY)
                barrier.wait(timeout=10)
                try:
                    result = confirm_import(
                        db,
                        user_id=user_id,
                        confirmation=form,
                        key=SIGNING_KEY,
                        idempotency_key="race-correction-new-key-0001",
                    )
                    assert not result.created_fact_ids
                    return "duplicate-skipped"
                except ConflictError as exc:
                    assert exc.code == "CV_CONFLICT"
                    return "conflict"

        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(correction)
            second = executor.submit(reimport)
            corrected_id = first.result(timeout=30)
            outcome = second.result(timeout=30)
        assert outcome in {"duplicate-skipped", "conflict"}

        with Session(migrated_engine) as db:
            active = list_facts(db, user_id)
            history = list_facts(db, user_id, include_history=True)
            assert len(active) == 1
            assert len(history) == 2
            assert str(active[0].id) == corrected_id
            assert active[0].supersedes_id == original_id
            assert {fact.status for fact in history} == {"ACTIVE", "SUPERSEDED"}
            assert master_profile(db, user_id)["items"][0]["id"] == corrected_id
    finally:
        _cleanup(migrated_engine, user_id)
