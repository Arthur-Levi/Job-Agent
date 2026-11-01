"""D2-E2.D: authenticated career facts with auditable corrections."""

import hashlib
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models import CandidateProfile, CareerFact


def list_facts(db: Session, user_id: UUID, include_history: bool = False) -> list[CareerFact]:
    stmt = select(CareerFact).where(CareerFact.user_id == user_id)
    if not include_history:
        stmt = stmt.where(CareerFact.status == "ACTIVE")
    return list(db.scalars(stmt.order_by(CareerFact.created_at, CareerFact.id)))


def correct_fact(db: Session, user_id: UUID, fact_id: UUID, value: str, reason: str) -> CareerFact:
    old = db.scalar(
        select(CareerFact)
        .where(CareerFact.user_id == user_id, CareerFact.id == fact_id)
        .with_for_update()
    )
    if old is None:
        raise NotFoundError("Fato não encontrado", code="CAREER_FACT_NOT_FOUND")
    if old.status != "ACTIVE":
        raise ConflictError("Fato já substituído ou rejeitado", code="CAREER_FACT_NOT_ACTIVE")
    # A revision is always user-declared, never inherits EXTERNALLY_VERIFIED.
    old.status = "SUPERSEDED"
    replacement = CareerFact(
        user_id=user_id,
        import_id=None,
        subject=old.subject,
        predicate=old.predicate,
        value=value,
        source_type="user_statement",
        source_reference=f"user-correction:{old.id}:reason-sha256:{hashlib.sha256(reason.encode()).hexdigest()}",
        verification="USER_DECLARED",
        status="ACTIVE",
        supersedes_id=old.id,
    )
    db.add(replacement)
    try:
        db.commit()
        db.refresh(replacement)
    except Exception:
        db.rollback()
        raise
    return replacement


def master_profile(db: Session, user_id: UUID) -> dict[str, Any]:
    profile = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user_id))
    # Master Profile view is grounded in the active ledger; absent facts remain absent.
    facts = list_facts(db, user_id)
    return {
        "profile_id": str(profile.id) if profile else None,
        "items": [
            {
                "id": str(fact.id),
                "category": fact.predicate,
                "title": fact.subject,
                "source_fact_ids": [str(fact.id)],
                "verification": fact.verification,
            }
            for fact in facts
        ],
    }
