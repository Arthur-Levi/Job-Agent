"""Authenticated Master Profile / Fact Ledger routes."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.api.deps import CurrentUserDep, SessionDep
from app.core.errors import error_responses
from app.schemas.career_import import FactRead
from app.schemas.vacancy_match import VacancyMatchRequest
from app.services.career_diagnostic import career_diagnostic
from app.services.career_facts import correct_fact, list_facts, master_profile
from app.services.evidence_resume import resume_draft
from app.services.resume_export import approved_export, export_preview
from app.services.vacancy_matching import vacancy_match

router = APIRouter(prefix="/career", tags=["career-facts"])


class Correction(BaseModel):
    value: str = Field(min_length=1, max_length=4000)
    reason: str = Field(min_length=3, max_length=300)


@router.get("/profile")
def read_career_profile(user: CurrentUserDep, session: SessionDep) -> dict[str, object]:
    return master_profile(session, user.id)


@router.get("/facts")
def read_facts(
    user: CurrentUserDep, session: SessionDep, include_history: bool = False
) -> dict[str, list[FactRead]]:
    return {
        "items": [
            FactRead.model_validate(fact) for fact in list_facts(session, user.id, include_history)
        ]
    }


@router.post(
    "/facts/{fact_id}/corrections",
    response_model=FactRead,
    status_code=201,
    responses=error_responses(401, 404, 409),
)
def revise_fact(
    fact_id: UUID,
    data: Correction,
    user: CurrentUserDep,
    session: SessionDep,
) -> FactRead:
    fact = correct_fact(session, user.id, fact_id, data.value, data.reason)
    return FactRead.model_validate(fact)


@router.get("/diagnostic")
def read_career_diagnostic(user: CurrentUserDep, session: SessionDep) -> dict[str, object]:
    """Evidence-backed preview only; missing facts are not missing abilities."""
    return career_diagnostic(session, user.id)


@router.get("/resume-draft")
def read_resume_draft(user: CurrentUserDep, session: SessionDep) -> dict[str, object]:
    """Candidate-review-only draft, never an unverified finalized resume."""
    return resume_draft(session, user.id)


@router.post("/vacancy-match")
def compare_vacancy(
    data: VacancyMatchRequest, user: CurrentUserDep, session: SessionDep
) -> dict[str, object]:
    """Read-only comparison; candidate-supplied vacancy requirements only."""
    return vacancy_match(session, user.id, data)


class ResumeExportApproval(BaseModel):
    approved: bool
    approval_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


@router.get("/resume-export/preview")
def review_resume_export(user: CurrentUserDep, session: SessionDep) -> dict[str, object]:
    """Review live ledger snapshot and approval digest before any file is created."""
    return export_preview(session, user)


@router.post("/resume-export/{format_name}", responses=error_responses(401, 409, 422))
def export_reviewed_resume(
    format_name: Literal["pdf", "docx"],
    data: ResumeExportApproval,
    user: CurrentUserDep,
    session: SessionDep,
) -> Response:
    payload = approved_export(session, user, format_name, data.approved, data.approval_sha256)
    media_type = (
        "application/pdf"
        if format_name == "pdf"
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    return Response(
        content=payload,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="job-agent-resume.{format_name}"',
            "Cache-Control": "no-store, private",
            "X-Content-Type-Options": "nosniff",
        },
    )
