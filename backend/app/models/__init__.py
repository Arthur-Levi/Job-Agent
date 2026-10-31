"""Importar todos os models aqui garante que Base.metadata esteja completo (Alembic/testes)."""

from app.models.application import Application, ApplicationEvent
from app.models.auth import AuthCredential, AuthSession
from app.models.candidate import (
    CandidateEducation,
    CandidateExperience,
    CandidateProfile,
    CandidateProject,
    CandidateSkill,
)
from app.models.job import Job, JobMatch, JobRequirement
from app.models.resume import ResumeVersion
from app.models.user import User

__all__ = [
    "Application",
    "AuthCredential",
    "AuthSession",
    "ApplicationEvent",
    "CandidateEducation",
    "CandidateExperience",
    "CandidateProfile",
    "CandidateProject",
    "CandidateSkill",
    "Job",
    "JobMatch",
    "JobRequirement",
    "ResumeVersion",
    "User",
]
