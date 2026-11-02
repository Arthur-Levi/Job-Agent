"""D2-E2.F.2: exact, transparent matching against active owned Fact Ledger.

Only structured and explicitly comparable values count. No semantic guessing,
no automated rejections, no scores and no external hiring/ATS predictions.
"""

import json
from collections import Counter
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.schemas.vacancy_match import VacancyMatchRequest, normalize_label
from app.services.career_facts import list_facts
from app.services.evidence_resume import _structured

DOCUMENTED = "documented_match"
UNKNOWN = "not_documented"
CONFLICT = "explicit_incompatibility"
MODES = {"remote_only", "onsite_only"}


def vacancy_match(db: Session, user_id: UUID, vacancy: VacancyMatchRequest) -> dict[str, Any]:
    # Only active facts belonging to this account; ignore superseded/history.
    facts = list_facts(db, user_id)
    structured: dict[tuple[str, str], list[dict[str, str]]] = {}
    modes: dict[str, list[dict[str, str]]] = {}

    for fact in facts:
        evidence = {
            "fact_id": str(fact.id),
            "title": fact.subject,
            "verification": fact.verification,
        }
        if fact.predicate in ("skill", "experience", "education", "project"):
            data = _structured(fact.value)
            # The structured title and subject must corroborate each other.
            if data is None or not data.get("title"):
                continue
            label = normalize_label(data["title"] or "")
            if label != normalize_label(fact.subject):
                continue
            structured.setdefault((fact.predicate, label), []).append(evidence)
        elif fact.predicate == "work_mode":
            try:
                data = json.loads(fact.value)
            except (ValueError, TypeError):
                continue
            if not isinstance(data, dict):
                continue
            mode = data.get("mode")
            if not isinstance(mode, str) or mode not in MODES:
                continue
            modes.setdefault(mode, []).append(evidence)

    # Conflicting active declarations are ambiguous, not proof of either position.
    mode_is_unambiguous = len(modes) == 1
    result: list[dict[str, Any]] = []

    for index, item in enumerate(vacancy.requirements, start=1):
        evidence: list[dict[str, str]] = []
        state = UNKNOWN
        explanation = (
            "Não há evidência estruturada exata deste requisito no Fact Ledger ativo. "
            "Isso não comprova ausência da competência ou experiência."
        )
        next_step = "Confira seus fatos e confirme informações reais antes de usar a análise."
        if item.category == "work_mode":
            if mode_is_unambiguous:
                known_mode = next(iter(modes))
                evidence = modes[known_mode]
                if known_mode == item.name:
                    state = DOCUMENTED
                    explanation = "Modalidade declarada coincide exatamente com o requisito informado."
                    next_step = "Confirme se a declaração ainda representa sua disponibilidade."
                else:
                    state = CONFLICT
                    explanation = (
                        "Há declaração ativa explícita de modalidade incompatível "
                        "com o requisito informado; confirme ambos os dados."
                    )
                    next_step = (
                        "Revise sua modalidade declarada e confira a modalidade da vaga. "
                        "Não presuma inelegibilidade sem validação humana."
                    )
            else:
                explanation = (
                    "Modalidade não documentada ou registros ativos contraditórios; "
                    "não é possível concluir compatibilidade."
                )
                next_step = "Confirme a modalidade de trabalho e os fatos antes de decidir."
        else:
            evidence = structured.get((item.category, normalize_label(item.name)), [])
            if evidence:
                state = DOCUMENTED
                explanation = (
                    "Correspondência textual exata entre o requisito informado e o "
                    "título de fato ativo estruturado. Não é validação externa."
                )
                next_step = "Confira se a evidência realmente atende ao contexto da vaga."

        result.append(
            {
                "position": index,
                "category": item.category,
                "name": item.name,
                "importance": item.importance,
                "classification": state,
                "evidence": evidence,
                "explanation": explanation,
                "next_step": next_step,
            }
        )

    counts = Counter(row["classification"] for row in result)
    return {
        "status": "preliminary_candidate_review",
        "basis": "active_fact_ledger_exact_match",
        "vacancy_title": vacancy.vacancy_title,
        "vacancy_source": "candidate_supplied_unverified",
        "requirements": result,
        "summary": {
            "total": len(result),
            "documented_match": counts[DOCUMENTED],
            "not_documented": counts[UNKNOWN],
            "explicit_incompatibility": counts[CONFLICT],
        },
        "limitations": [
            "Requisitos informados pelo candidato não foram verificados com o empregador.",
            "Correspondências exigem igualdade textual e não inferem sinônimos ou senioridade.",
            "Não documentado não significa incapacidade nem falta real da competência.",
            "Incompatibilidade explícita só é indicada para modalidade declarada sem ambiguidade.",
            "Não há nota de empregabilidade, previsão de contratação ou avaliação ATS.",
            "Nenhum fato ou vaga é salvo ou modificado por esta análise.",
        ],
    }
