"""D2-E2.E — read-only, evidence-grounded career diagnostic.

No generated claims, scores, skills inference, job guarantees or external lookups.
A missing fact means *not documented in the ledger*, never 'candidate lacks it'.
"""

import json
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.services.career_facts import list_facts

CATEGORIES = ("experience", "education", "project", "skill")
CATEGORY_TITLES = {
    "experience": "Experiências profissionais",
    "education": "Formação",
    "project": "Projetos",
    "skill": "Competências declaradas",
}


def career_diagnostic(db: Session, user_id: UUID) -> dict[str, Any]:
    facts = list_facts(db, user_id)
    categories: dict[str, list[dict[str, str]]] = {name: [] for name in CATEGORIES}
    review: list[dict[str, Any]] = []

    for fact in facts:
        if fact.predicate not in categories:
            # Unknown predicates are not silently recast into a known skill.
            continue
        evidence = {
            "fact_id": str(fact.id),
            "title": fact.subject,
            "verification": fact.verification,
        }
        categories[fact.predicate].append(evidence)
        if fact.predicate != "experience":
            continue
        try:
            data = json.loads(fact.value)
        except (ValueError, TypeError):
            data = None
        if not isinstance(data, dict):
            continue
        missing = [
            field
            for field in ("organization", "start_date")
            if not isinstance(data.get(field), str) or not data[field].strip()
        ]
        if missing:
            review.append(
                {
                    "kind": "review_documented_fact",
                    "fact_id": str(fact.id),
                    "fields": missing,
                    "message": "Revise informações não preenchidas nesta experiência.",
                }
            )

    coverage: list[dict[str, Any]] = []
    for category in CATEGORIES:
        documented = categories[category]
        coverage.append(
            {
                "category": category,
                "title": CATEGORY_TITLES[category],
                "state": "documented" if documented else "not_documented",
                "count": len(documented),
                "evidence": documented,
            }
        )
        if not documented:
            review.append(
                {
                    "kind": "verify_missing_records",
                    "category": category,
                    "message": (
                        "Não há registros desta categoria no Fact Ledger. "
                        "Isso não significa que você não tenha essa experiência."
                    ),
                }
            )

    return {
        "status": "preliminary",
        "basis": "active_fact_ledger",
        "total_active_facts": len(facts),
        "coverage": coverage,
        "review_actions": review,
        "limitations": [
            "Dados declarados pelo candidato não são verificação independente.",
            "Ausência de registro não comprova ausência de experiência ou competência.",
            "Este diagnóstico não prevê aprovação em ATS, entrevistas ou contratação.",
            "Nenhum fato foi criado ou alterado por esta análise.",
        ],
    }
