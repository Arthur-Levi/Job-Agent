"""Seed de DESENVOLVIMENTO.

- Só roda com APP_ENV=development (guard em `ensure_development`); nunca é chamado pela aplicação.
- Idempotente: rodar de novo não duplica nada.
- Dados evidentemente fictícios: URLs em `.invalid` (TLD reservado, não resolve), empresas
  "Example", textos marcados "[DEV SEED]".
- Usa os mesmos services da API (regras, transações e eventos reais) e pertence ao usuário
  padrão, o mesmo que o frontend enxerga.

Uso:  python -m app.devtools.seed     (a partir de backend/)
"""

import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import AppEnv, Settings
from app.db.session import Database
from app.domain.enums import ApplicationStatus, EmploymentType, Seniority, WorkModel
from app.repositories.application import ApplicationRepository
from app.repositories.candidate_profile import CandidateProfileRepository
from app.repositories.job import JobRepository
from app.repositories.user import UserRepository
from app.schemas.application import ApplicationCreate, ApplicationUpdate
from app.schemas.job import JobCreate
from app.schemas.profile import ProfileCreate
from app.services.application import ApplicationService
from app.services.candidate_profile import CandidateProfileService
from app.services.job import JobService
from app.services.user import UserService

SEED_SOURCE = "dev-seed"


class SeedNotAllowedError(RuntimeError):
    pass


@dataclass
class SeedReport:
    created: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def ensure_development(settings: Settings) -> None:
    if settings.app_env is not AppEnv.DEVELOPMENT:
        raise SeedNotAllowedError(
            f"Seed is only allowed with APP_ENV=development (current: {settings.app_env.value})."
        )


def _seed_jobs() -> tuple[JobCreate, JobCreate]:
    return (
        JobCreate(
            title="Backend Developer (sample)",
            company="Example Corp",
            description="[DEV SEED] Sample posting used only for local development.\n"
            "Build and maintain REST APIs with Python and PostgreSQL.",
            source=SEED_SOURCE,
            source_url="https://dev-seed.invalid/jobs/backend-developer",
            location="Remote",
            work_model=WorkModel.REMOTE,
            employment_type=EmploymentType.FULL_TIME,
            seniority=Seniority.JUNIOR,
            salary_min=Decimal("5000"),
            salary_max=Decimal("8000"),
            currency="BRL",
            published_at=datetime(2026, 10, 1, tzinfo=UTC),
        ),
        JobCreate(
            title="Software Engineering Intern (sample)",
            company="Sample Labs",
            description="[DEV SEED] Sample internship posting used only for local development.",
            source=SEED_SOURCE,
            source_url="https://dev-seed.invalid/jobs/software-intern",
            location="São Paulo, SP",
            work_model=WorkModel.HYBRID,
            employment_type=EmploymentType.INTERNSHIP,
            seniority=Seniority.INTERN,
            published_at=datetime(2026, 10, 3, tzinfo=UTC),
        ),
    )


def seed_development_data(session: Session, settings: Settings) -> SeedReport:
    ensure_development(settings)
    report = SeedReport()

    user_repo = UserRepository(session)
    existed = user_repo.get_by_email(settings.default_user_email) is not None
    user = UserService(
        user_repo,
        session,
        default_email=settings.default_user_email,
        default_name=settings.default_user_name,
    ).get_or_create_default()
    (report.skipped if existed else report.created).append("user")

    profile_repo = CandidateProfileRepository(session)
    if profile_repo.get_by_user_id(user.id) is None:
        CandidateProfileService(profile_repo, session).create(
            user,
            ProfileCreate(
                headline="[DEV SEED] Backend developer (sample profile)",
                summary="Sample profile created by the development seed.",
                city="São Paulo",
                state="SP",
                country="Brasil",
                desired_work_model=WorkModel.REMOTE,
                desired_seniority=Seniority.JUNIOR,
            ),
        )
        report.created.append("profile")
    else:
        report.skipped.append("profile")

    job_repo = JobRepository(session)
    job_service = JobService(job_repo, session)
    jobs = []
    for spec in _seed_jobs():
        if spec.source_url is None:
            raise ValueError("seed jobs must have a source_url")
        job = job_repo.get_by_source_url(user.id, spec.source_url)
        if job is None:
            job = job_service.create(user, spec)
            report.created.append(f"job: {spec.title}")
        else:
            report.skipped.append(f"job: {spec.title}")
        jobs.append(job)

    app_repo = ApplicationRepository(session)
    first_job = jobs[0]
    if not app_repo.list_page(user.id, status=None, job_id=first_job.id, limit=1, offset=0):
        service = ApplicationService(app_repo, job_repo, session)
        application = service.create(user, ApplicationCreate(job_id=first_job.id)).application
        service.update(user, application.id, ApplicationUpdate(status=ApplicationStatus.QUALIFIED))
        report.created.append("application")
    else:
        report.skipped.append("application")
    return report


def main() -> int:
    settings = Settings()
    try:
        ensure_development(settings)
    except SeedNotAllowedError as exc:
        print(f"Refusing to seed: {exc}", file=sys.stderr)
        return 2

    print(f"Seeding development data into {settings.safe_database_url}")
    database = Database(settings)
    session = database.new_session()
    try:
        report = seed_development_data(session, settings)
    finally:
        session.close()
        database.dispose()
    print(f"created: {', '.join(report.created) or '-'}")
    print(f"already present: {', '.join(report.skipped) or '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
