"""D2-E2.F.2: explain an owned, saved job using the EXISTING Fact Ledger matcher.

Read-only. Does not infer missing fields, scores, eligibility or ATS odds.
Incomplete/unclassified JobRequirement rows require human review; they never
silently become "matched". No document parser or real CV intake is invoked.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, UnprocessableError
from app.domain.enums import RequirementImportance
from app.models import Job, JobRequirement
from app.schemas.vacancy_match import VacancyMatchRequest, VacancyRequirement
from app.services.vacancy_matching import vacancy_match

_CATEGORIES = {"skill", "experience", "education", "project", "work_mode"}
_IMPORTANCE = {
    RequirementImportance.MUST_HAVE: "required",
    RequirementImportance.IMPORTANT: "preferred",
    RequirementImportance.NICE_TO_HAVE: "preferred",
}


def explain_saved_job(db: Session, user_id: UUID, job_id: UUID) -> dict[str, Any]:
    """Owner-scoped job -> explicit requirements -> existing exact ledger matcher.

    A saved job description is deliberately NOT parsed with heuristic keywords.
    Operators must attach categorized requirements first.
    """
    job = db.scalar(select(Job).where(Job.id == job_id, Job.user_id == user_id))
    if job is None:
        raise NotFoundError("Vaga não encontrada", code="JOB_NOT_FOUND")

    requirements = list(
        db.scalars(
            select(JobRequirement)
            .where(JobRequirement.job_id == job.id)
            .order_by(JobRequirement.name, JobRequirement.id)
        )
    )
    if not requirements:
        raise UnprocessableError(
            "Adicione requisitos estruturados à vaga antes de comparar.",
            code="MATCH_REQUIREMENTS_REQUIRED",
        )
    if len(requirements) > 20:
        raise UnprocessableError(
            "A análise aceita no máximo 20 requisitos explícitos.",
            code="MATCH_REQUIREMENTS_LIMIT",
        )

    items: list[VacancyRequirement] = []
    for item in requirements:
        category = (item.category or "").strip().lower()
        importance = _IMPORTANCE.get(item.importance)
        name = item.normalized_name or item.name
        if category not in _CATEGORIES or importance is None:
            raise UnprocessableError(
                "A vaga contém requisitos sem categoria ou prioridade confirmada.",
                code="MATCH_REQUIREMENTS_REVIEW",
            )
        if category == "work_mode" and name not in {"remote_only", "onsite_only"}:
            raise UnprocessableError(
                "A modalidade precisa ser confirmada antes da comparação.",
                code="MATCH_REQUIREMENTS_REVIEW",
            )
        # Pydantic also rejects malformed, duplicated, oversized requirements.
        try:
            items.append(
                VacancyRequirement(
                    category=category,
                    name=name,
                    importance=importance,
                )
            )
        except ValueError:
            raise UnprocessableError(
                "Revise o preenchimento dos requisitos da vaga.",
                code="MATCH_REQUIREMENTS_REVIEW",
            ) from None

    try:
        request = VacancyMatchRequest(vacancy_title=job.title, requirements=items)
    except ValueError:
        raise UnprocessableError(
            "Revise requisitos duplicados ou inválidos antes de comparar.",
            code="MATCH_REQUIREMENTS_REVIEW",
        ) from None

    result = vacancy_match(db, user_id, request)
    return {
        **result,
        "saved_job_id": str(job.id),
        "vacancy_source": "owned_saved_job_requirements_unverified",
        "limitations": [
            *result["limitations"],
            "O texto livre da vaga não foi interpretado; apenas requisitos estruturados contam.",
            "Importância MUST_HAVE é tratada como required; IMPORTANT/NICE_TO_HAVE como preferred.",
            "Itens UNKNOWN ou sem categoria exigem revisão e bloqueiam esta análise.",
        ],
    }
