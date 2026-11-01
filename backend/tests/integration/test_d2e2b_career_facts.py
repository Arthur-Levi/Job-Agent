"""D2-E2.B ownership and integrity on the ephemeral CI *_test PostgreSQL only."""

import hashlib
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import CareerFact, ResumeImportRecord, User


def make_user(db_session: Session) -> User:
    user = User(name="Synthetic Candidate", email=f"synthetic-{uuid4()}@example.invalid")
    db_session.add(user)
    db_session.flush()
    return user


def make_import(
    db_session: Session, user: User, key: str = "synthetic-idempotency-key-001"
) -> ResumeImportRecord:
    imp = ResumeImportRecord(
        user_id=user.id,
        idempotency_key=key,
        content_sha256=hashlib.sha256(b"Synthetic confirmed fields only").hexdigest(),
        source_format="txt",
    )
    db_session.add(imp)
    db_session.flush()
    return imp


def make_fact(
    user: User,
    *,
    import_id: UUID | None = None,
    source_type: str = "user_statement",
    supersedes_id: UUID | None = None,
) -> CareerFact:
    return CareerFact(
        user_id=user.id,
        import_id=import_id,
        subject="Projeto sintético",
        predicate="descricao_profissional",
        value="Construção de dashboards sintéticos",
        source_type=source_type,
        source_reference="test-only",
        verification="USER_DECLARED",
        status="ACTIVE",
        supersedes_id=supersedes_id,
    )


def test_one_user_can_store_confirmed_import_and_owned_fact(db_session: Session) -> None:
    user = make_user(db_session)
    receipt = make_import(db_session, user)
    fact = make_fact(user, import_id=receipt.id, source_type="resume_import")
    db_session.add(fact)
    db_session.flush()
    assert fact.id is not None
    assert (
        db_session.scalar(
            select(CareerFact).where(CareerFact.id == fact.id, CareerFact.user_id == user.id)
        )
        is fact
    )


def test_same_import_key_in_different_users_is_allowed(db_session: Session) -> None:
    one = make_user(db_session)
    two = make_user(db_session)
    make_import(db_session, one)
    make_import(db_session, two)
    assert len(db_session.scalars(select(ResumeImportRecord)).all()) == 2


def test_duplicate_import_key_within_one_user_is_rejected(db_session: Session) -> None:
    user = make_user(db_session)
    make_import(db_session, user)
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(
            ResumeImportRecord(
                user_id=user.id,
                idempotency_key="synthetic-idempotency-key-001",
                content_sha256="0" * 64,
                source_format="txt",
            )
        )
        db_session.flush()


def test_cross_user_import_reference_is_rejected(db_session: Session) -> None:
    one = make_user(db_session)
    two = make_user(db_session)
    receipt = make_import(db_session, one)
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(make_fact(two, import_id=receipt.id, source_type="resume_import"))
        db_session.flush()


def test_cross_user_fact_supersession_is_rejected(db_session: Session) -> None:
    one = make_user(db_session)
    two = make_user(db_session)
    previous = make_fact(one)
    db_session.add(previous)
    db_session.flush()
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(make_fact(two, supersedes_id=previous.id))
        db_session.flush()


def test_fact_without_import_cannot_claim_resume_import_origin(db_session: Session) -> None:
    user = make_user(db_session)
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(make_fact(user, source_type="resume_import"))
        db_session.flush()


def test_correction_history_can_coexist_without_mutating_prior_value(db_session: Session) -> None:
    user = make_user(db_session)
    old = make_fact(user)
    db_session.add(old)
    db_session.flush()
    old.status = "SUPERSEDED"
    updated = make_fact(user, supersedes_id=old.id)
    updated.value = "Relatórios sintéticos em Power BI e Excel"
    db_session.add(updated)
    db_session.flush()
    assert old.value == "Construção de dashboards sintéticos"
    assert updated.supersedes_id == old.id
    assert updated.user_id == old.user_id
    assert db_session.scalars(select(CareerFact).where(CareerFact.user_id == user.id)).all() == [
        old,
        updated,
    ]


def test_resume_import_does_not_store_original_document(db_session: Session) -> None:
    user = make_user(db_session)
    receipt = make_import(db_session, user)
    assert not hasattr(receipt, "raw_file")
    assert not hasattr(receipt, "extracted_text")
    assert not hasattr(receipt, "filename")
