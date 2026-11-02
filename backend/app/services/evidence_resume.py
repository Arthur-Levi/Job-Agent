"""D2-E2.F.1: conservative resume draft from active, owned Fact Ledger entries.

No free-form generation, inference, fake achievements, external lookups or writes.
Every entry cites its exact active source fact ID.
"""

import json
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.services.career_facts import list_facts

CATEGORIES = ("experience", "education", "project", "skill")
MAX_ENTRIES = 80


def _structured(value: str) -> dict[str, str | None] | None:
    try:
        raw = json.loads(value)
    except (ValueError, TypeError):
        return None
    if not isinstance(raw, dict):
        return None
    result: dict[str, str | None] = {}
    for field in ("title", "description", "organization", "start_date", "end_date"):
        item = raw.get(field)
        if item is None:
            result[field] = None
        elif isinstance(item, str):
            result[field] = item.strip()[:4000] or None
        else:
            return None
    return result


def resume_draft(db: Session, user_id: UUID) -> dict[str, Any]:
    sections: list[dict[str, Any]] = [
        {"category": category, "entries": []} for category in CATEGORIES
    ]
    by_category = {section["category"]: section["entries"] for section in sections}
    omitted: list[dict[str, str]] = []
    facts = list_facts(db, user_id)

    for fact in facts[:MAX_ENTRIES]:
        if fact.predicate not in by_category:
            omitted.append({"fact_id": str(fact.id), "reason": "unsupported_category"})
            continue
        data = _structured(fact.value)
        if data is None:
            omitted.append({"fact_id": str(fact.id), "reason": "unstructured_fact"})
            continue
        # Display only actual structured values, never interpolate missing data.
        entry = {
            "fact_id": str(fact.id),
            "verification": fact.verification,
            "title": fact.subject,
            "description": data["description"],
            "organization": data["organization"],
            "start_date": data["start_date"],
            "end_date": data["end_date"],
            "requires_review": any(data[field] is None for field in ("description", "organization"))
            if fact.predicate == "experience"
            else False,
        }
        by_category[fact.predicate].append(entry)

    if len(facts) > MAX_ENTRIES:
        omitted.append({"fact_id": "overflow", "reason": "entry_limit"})

    return {
        "status": "draft_requires_candidate_review",
        "basis": "active_fact_ledger",
        "sections": sections,
        "omitted": omitted,
        "limitations": [
            "Somente dados ativos declarados ou registrados no Fact Ledger.",
            "Nenhum cargo, competência, resultado ou data foi inferido.",
            "Esta versão não realiza exportação, personalização ou envio de currículo.",
            "O candidato deve revisar e aprovar as informações antes de usá-las.",
        ],
    }
