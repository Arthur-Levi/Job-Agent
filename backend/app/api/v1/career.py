"""Authenticated Master Profile / Fact Ledger routes."""

from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.deps import CurrentUserDep, SessionDep
from app.core.errors import error_responses
from app.schemas.career_import import FactRead
from app.services.career_diagnostic import career_diagnostic
from app.services.career_facts import correct_fact, list_facts, master_profile

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
