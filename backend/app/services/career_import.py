"""Atomic confirmation of human-reviewed CV drafts and traceable profile projection.

No LLM claims, no externally verified status, no automatic job application.
"""
import hashlib
import json
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, UnprocessableError
from app.models import (
    CandidateEducation,
    CandidateExperience,
    CandidateProfile,
    CandidateProject,
    CandidateSkill,
    CareerFact,
    ResumeImportRecord,
)
from app.schemas.career_import import ConfirmResult, ImportConfirmation
from app.services.preview_ticket import verify_preview


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _canonical(item: Any) -> dict[str, Any]:
    return {
        "draft_id": str(item.draft_id),
        "category": item.category,
        "title": item.title,
        "description": item.description,
        "organization": item.organization,
        "start_date": item.start_date,
        "end_date": item.end_date,
        "review_status": item.review_status,
        "source_excerpt": item.source_excerpt,
    }


def _fact_value(item: Any) -> str:
    return _json({
        "title": item.title,
        "description": item.description,
        "organization": item.organization,
        "start_date": item.start_date,
        "end_date": item.end_date,
    })


def _project(db: Session, profile_id: UUID, item: Any) -> None:
    """Projection from a confirmed fact; original year precision retained in fact JSON.

    CandidateExperience uses full dates, therefore partial dates are not falsely
    expanded to January 1 or December 31; fields remain NULL until user supplies
    exact dates in a dedicated editor.
    """
    if item.category == "experience" and item.organization:
        db.add(
            CandidateExperience(
                candidate_profile_id=profile_id,
                company=item.organization,
                title=item.title,
                description=item.description,
                start_date=None,
                end_date=None,
                current=item.end_date is not None and item.end_date.lower() in ("atual", "presente"),
            )
        )
    elif item.category == "education" and item.organization:
        db.add(
            CandidateEducation(
                candidate_profile_id=profile_id,
                institution=item.organization,
                course=item.title,
                degree=None,
                start_date=None,
                end_date=None,
            )
        )
    elif item.category == "project":
        db.add(
            CandidateProject(
                candidate_profile_id=profile_id,
                name=item.title,
                description=item.description,
                url=None,
            )
        )
    elif item.category == "skill" and len(item.title) <= 100:
        existing = db.scalar(
            select(CandidateSkill).where(
                CandidateSkill.candidate_profile_id == profile_id,
                CandidateSkill.name.ilike(item.title),
            )
        )
        if existing is None:
            db.add(CandidateSkill(candidate_profile_id=profile_id, name=item.title))


def confirm_import(
    db: Session,
    *,
    user_id: UUID,
    confirmation: ImportConfirmation,
    key: bytes,
    idempotency_key: str,
) -> ConfirmResult:
    signed = verify_preview(confirmation.preview_ticket, user_id=str(user_id), key=key)
    if str(confirmation.preview_id) != signed["preview_id"]:
        raise UnprocessableError("Referência da prévia não corresponde", code="CV_PREVIEW")
    original: dict[str, dict[str, Any]] = {
        item["draft_id"]: item for item in signed["items"]
    }
    if len(original) != len(signed["items"]) or len(confirmation.items) != len(original):
        raise UnprocessableError("Itens ausentes ou repetidos", code="CV_ITEMS")
    seen: set[str] = set()
    for item in confirmation.items:
        identity = str(item.draft_id)
        source = original.get(identity)
        if (
            source is None
            or identity in seen
            or item.category != source["category"]
            or item.source_excerpt != source["source_excerpt"]
        ):
            raise UnprocessableError("Origem ou identidade alterada", code="CV_ITEMS")
        seen.add(identity)

    canonical = [_canonical(item) for item in confirmation.items]
    digest = hashlib.sha256(_json({"items": canonical, "preview_id": signed["preview_id"]}).encode()).hexdigest()
    existing = db.scalar(
        select(ResumeImportRecord).where(
            ResumeImportRecord.user_id == user_id,
            ResumeImportRecord.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        if existing.content_sha256 != digest:
            raise ConflictError("Chave de idempotência reutilizada com conteúdo diferente", code="CV_REPLAY")
        facts = db.scalars(
            select(CareerFact).where(
                CareerFact.user_id == user_id, CareerFact.import_id == existing.id
            )
        ).all()
        return ConfirmResult(
            import_id=existing.id,
            created_fact_ids=[fact.id for fact in facts],
            skipped_duplicates=[],
        )

    active = db.scalars(
        select(CareerFact).where(CareerFact.user_id == user_id, CareerFact.status == "ACTIVE")
    ).all()
    signatures = {(fact.predicate, fact.subject.casefold(), fact.value): fact for fact in active}
    # Same category, title, company and period with a different description needs review.
    identities: dict[tuple[str, str, str, str, str], str] = {}
    for fact in active:
        try:
            value = json.loads(fact.value)
            identity = (
                fact.predicate, fact.subject.casefold(),
                (value.get("organization") or "").casefold(),
                value.get("start_date") or "", value.get("end_date") or "",
            )
            identities[identity] = fact.value
        except (ValueError, AttributeError):
            continue

    accepted = [item for item in confirmation.items if item.review_status != "rejected"]
    if not accepted:
        raise UnprocessableError("Selecione ao menos um item para salvar", code="CV_EMPTY")

    # Validate conflicts BEFORE adding any rows; all other writes share one DB transaction.
    new_items: list[Any] = []
    skipped: list[UUID] = []
    for item in accepted:
        value = _fact_value(item)
        signature = (item.category, item.title.casefold(), value)
        if signature in signatures:
            skipped.append(signatures[signature].id)
            continue
        identity = (
            item.category, item.title.casefold(), (item.organization or "").casefold(),
            item.start_date or "", item.end_date or "",
        )
        if identity in identities and identities[identity] != value:
            raise ConflictError(
                "Experiência ou formação semelhante exige resolução manual", code="CV_CONFLICT"
            )
        identities[identity] = value
        new_items.append(item)

    receipt = ResumeImportRecord(
        user_id=user_id,
        idempotency_key=idempotency_key,
        content_sha256=digest,
        source_format=signed["format"],
    )
    try:
        db.add(receipt)
        db.flush()
        profile = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user_id))
        if profile is None:
            profile = CandidateProfile(user_id=user_id)
            db.add(profile)
            db.flush()
        created: list[UUID] = []
        for item in new_items:
            fact = CareerFact(
                user_id=user_id,
                import_id=receipt.id,
                subject=item.title,
                predicate=item.category,
                value=_fact_value(item),
                source_type="resume_import",
                source_reference=f"resume-preview:{signed['preview_id']}:{item.draft_id}",
                verification="USER_DECLARED",
                status="ACTIVE",
            )
            db.add(fact)
            db.flush()
            created.append(fact.id)
            _project(db, profile.id, item)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("Importação concorrente; consulte fatos e tente novamente", code="CV_CONCURRENT") from exc
    except Exception:
        db.rollback()
        raise
    return ConfirmResult(
        import_id=receipt.id, created_fact_ids=created, skipped_duplicates=skipped
    )
