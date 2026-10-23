from fastapi import APIRouter

from app.api.deps import ReadinessServiceDep
from app.core.errors import ErrorResponse, ServiceUnavailableError
from app.schemas.health import HealthResponse, ReadyResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness: o processo responde. Não toca em dependências."""
    return HealthResponse(status="ok")


@router.get("/ready", response_model=ReadyResponse, responses={503: {"model": ErrorResponse}})
def ready(service: ReadinessServiceDep) -> ReadyResponse:
    """Readiness: só responde 200 se o banco estiver acessível."""
    report = service.check()
    if not report.database_ok:
        raise ServiceUnavailableError("Database is not reachable", code="DATABASE_UNAVAILABLE")
    return ReadyResponse(status="ready", checks={"database": "ok"})
