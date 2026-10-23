from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class Constraint:
    """Nomes de constraints usados para mapear violações em erros de negócio.

    Um teste garante que cada nome existe no schema (renomear sem atualizar quebra a suíte).
    """

    CANDIDATE_PROFILE_USER = "uq_candidate_profiles_user_id"
    JOB_SOURCE_URL = "uq_jobs_user_id_source_url"
    JOB_HAS_APPLICATIONS = "fk_applications_job_id_jobs"
    APPLICATION_USER_JOB = "uq_applications_user_id_job_id"


class ConstraintViolationError(Exception):
    """Violação de integridade traduzida, sem expor SQLAlchemy/driver para os services."""

    def __init__(self, constraint: str | None) -> None:
        self.constraint = constraint
        super().__init__(f"constraint violated: {constraint}")


def flush(session: Session) -> None:
    """flush() que traduz IntegrityError. O rollback é responsabilidade de quem chama (service)."""
    try:
        session.flush()
    except IntegrityError as exc:
        diag = getattr(exc.orig, "diag", None)
        raise ConstraintViolationError(getattr(diag, "constraint_name", None)) from exc
