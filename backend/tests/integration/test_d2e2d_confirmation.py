"""D2-E2.D integration acceptance: only CI's disposable PostgreSQL *_test.

Do not run this module on the preserved Codespaces database. The integration
fixture DROPS the public schema and recreates migrations from scratch.
"""
import uuid
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, UnprocessableError
from app.models import CandidateProfile, CareerFact, ResumeImportRecord, User
from app.schemas.career_import import ImportConfirmation
from app.services.career_facts import correct_fact, list_facts, master_profile
from app.services.career_import import confirm_import
from app.services.preview_ticket import sign_preview, verify_preview


def _user(db: Session) -> User:
    user = User(name="Synthetic Tester", email=f"user-{uuid.uuid4()}@example.invalid")
    db.add(user)
    db.flush()
    return user


def _preview() -> dict[str, Any]:
    return {
        "preview_id": str(uuid.uuid4()),
        "format": "txt",
        "items": [
            {
                "draft_id": str(uuid.uuid4()),
                "category": "experience",
                "title": "Analista de Dados",
                "description": "Dashboards sintéticos de Excel e Power BI",
                "organization": "Empresa Exemplo",
                "start_date": "2023",
                "end_date": "2024",
                "source_excerpt": "Empresa Exemplo | Analista de Dados | 2023-2024",
            }
        ],
    }


def _confirmation(preview: dict[str, Any], user: User, key: bytes) -> ImportConfirmation:
    ticket = sign_preview(preview, user_id=str(user.id), key=key)
    return ImportConfirmation.model_validate(
        {
            "preview_id": preview["preview_id"],
            "preview_ticket": ticket,
            "confirmed": True,
            "items": [{**preview["items"][0], "review_status": "confirmed"}],
        }
    )


def test_signed_ticket_rejects_wrong_user_and_tampering(db_session: Session) -> None:
    a = _user(db_session)
    b = _user(db_session)
    preview = _preview()
    key = b"synthetic-key-32chars-long-not-production"
    ticket = sign_preview(preview, user_id=str(a.id), key=key)
    with pytest.raises(UnprocessableError):
        verify_preview(ticket, user_id=str(b.id), key=key)
    with pytest.raises(UnprocessableError):
        verify_preview(ticket[:-2] + "00", user_id=str(a.id), key=key)


def test_ticket_expires_and_rejects_future_time(db_session: Session) -> None:
    a = _user(db_session)
    key = b"synthetic-key-32chars-long-not-production"
    ticket = sign_preview(_preview(), user_id=str(a.id), key=key, now=1000)
    assert verify_preview(ticket, user_id=str(a.id), key=key, now=1001)
    with pytest.raises(UnprocessableError):
        verify_preview(ticket, user_id=str(a.id), key=key, now=1000 + 901)


def test_confirm_creates_owned_receipt_facts_master_profile(db_session: Session) -> None:
    user = _user(db_session)
    key = b"synthetic-key-32chars-long-not-production"
    confirmation = _confirmation(_preview(), user, key)
    result = confirm_import(
        db_session, user_id=user.id, confirmation=confirmation,
        key=key, idempotency_key="test-key-first-import-001",
    )
    assert len(result.created_fact_ids) == 1
    assert result.verification == "USER_DECLARED"
    fact = db_session.get(CareerFact, result.created_fact_ids[0])
    assert fact is not None
    assert fact.user_id == user.id
    assert fact.source_type == "resume_import"
    assert fact.verification == "USER_DECLARED"
    assert db_session.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
    profile = master_profile(db_session, user.id)
    assert len(profile["items"]) == 1
    assert profile["items"][0]["source_fact_ids"] == [str(fact.id)]
    assert db_session.scalar(
        select(ResumeImportRecord).where(ResumeImportRecord.user_id == user.id)
    ) is not None


def test_idempotent_retry_does_not_duplicate_facts(db_session: Session) -> None:
    user = _user(db_session)
    key = b"synthetic-key-32chars-long-not-production"
    confirmation = _confirmation(_preview(), user, key)
    results = [
        confirm_import(
            db_session, user_id=user.id, confirmation=confirmation,
            key=key, idempotency_key="test-idempotent-key-001",
        ) for _ in range(2)
    ]
    assert results[0].import_id == results[1].import_id
    assert results[0].created_fact_ids == results[1].created_fact_ids
    assert len(list_facts(db_session, user.id)) == 1


def test_new_key_exact_repeat_skips_duplicate(db_session: Session) -> None:
    user = _user(db_session)
    key = b"synthetic-key-32chars-long-not-production"
    first = _confirmation(_preview(), user, key)
    confirm_import(
        db_session, user_id=user.id, confirmation=first,
        key=key, idempotency_key="test-key-unique-one-001",
    )
    second = _confirmation(_preview(), user, key)
    result = confirm_import(
        db_session, user_id=user.id, confirmation=second,
        key=key, idempotency_key="test-key-unique-two-002",
    )
    assert not result.created_fact_ids
    assert len(result.skipped_duplicates) == 1
    assert len(list_facts(db_session, user.id)) == 1


def test_payload_reuse_of_key_is_conflict(db_session: Session) -> None:
    user = _user(db_session)
    key = b"synthetic-key-32chars-long-not-production"
    first = _confirmation(_preview(), user, key)
    confirm_import(
        db_session, user_id=user.id, confirmation=first,
        key=key, idempotency_key="test-replay-conflict-001",
    )
    edited = first.model_copy(deep=True)
    edited.items[0].description = "Outra experiência corrigida"
    with pytest.raises(ConflictError):
        confirm_import(
            db_session, user_id=user.id, confirmation=edited,
            key=key, idempotency_key="test-replay-conflict-001",
        )


def test_source_tampering_rejected_before_writes(db_session: Session) -> None:
    user = _user(db_session)
    key = b"synthetic-key-32chars-long-not-production"
    edited = _confirmation(_preview(), user, key)
    edited.items[0].source_excerpt = "Inventado fora do documento"
    with pytest.raises(UnprocessableError):
        confirm_import(
            db_session, user_id=user.id, confirmation=edited,
            key=key, idempotency_key="test-source-tampering-001",
        )
    assert db_session.scalars(
        select(ResumeImportRecord).where(ResumeImportRecord.user_id == user.id)
    ).all() == []


def test_other_user_cannot_confirm_ticket(db_session: Session) -> None:
    a = _user(db_session)
    b = _user(db_session)
    key = b"synthetic-key-32chars-long-not-production"
    form = _confirmation(_preview(), a, key)
    with pytest.raises(UnprocessableError):
        confirm_import(
            db_session, user_id=b.id, confirmation=form,
            key=key, idempotency_key="test-cross-user-block-001",
        )
    assert list_facts(db_session, b.id) == []


def test_correction_supersedes_and_protects_cross_user(db_session: Session) -> None:
    a = _user(db_session)
    b = _user(db_session)
    key = b"synthetic-key-32chars-long-not-production"
    created = confirm_import(
        db_session, user_id=a.id, confirmation=_confirmation(_preview(), a, key),
        key=key, idempotency_key="test-correction-history-001",
    )
    fact_id = created.created_fact_ids[0]
    with pytest.raises(NotFoundError):
        correct_fact(db_session, b.id, fact_id, "Qualquer texto", "Ajuste")
    corrected = correct_fact(
        db_session, a.id, fact_id, "Atuei em relatórios sintéticos", "Informação imprecisa"
    )
    assert corrected.supersedes_id == fact_id
    assert corrected.verification == "USER_DECLARED"
    assert len(list_facts(db_session, a.id)) == 1
    assert len(list_facts(db_session, a.id, include_history=True)) == 2
    assert master_profile(db_session, a.id)["items"][0]["id"] == str(corrected.id)
    with pytest.raises(ConflictError):
        correct_fact(db_session, a.id, fact_id, "Repetição", "Tentativa")
