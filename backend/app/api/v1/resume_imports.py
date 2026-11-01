"""D2-E2.C/D: authenticated CV preview and explicit confirmation."""

from typing import Annotated

from fastapi import APIRouter, File, Header, Request, UploadFile
from starlette.concurrency import run_in_threadpool

from app.api.deps import CurrentUserDep, SessionDep, SettingsDep
from app.core.errors import ServiceUnavailableError, UnprocessableError, error_responses
from app.schemas.career_import import ConfirmResult, ImportConfirmation
from app.services.career_import import confirm_import
from app.services.preview_ticket import sign_preview
from app.services.resume_preview import MAX_FILE_BYTES
from app.services.resume_worker import parse_in_worker

router = APIRouter(prefix="/resume-imports", tags=["resume-imports"])


def preview_key(request: Request, settings: SettingsDep) -> bytes:
    if settings.is_production and (
        settings.resume_preview_signing_secret is None
        or len(settings.resume_preview_signing_secret.get_secret_value()) < 32
    ):
        raise ServiceUnavailableError(
            "Configuração de assinatura indisponível", code="CV_SIGNING_UNAVAILABLE"
        )
    key: bytes = request.app.state.resume_preview_key
    return key


@router.post("/preview", responses=error_responses(401, 413, 422, 503))
async def preview_resume(
    user: CurrentUserDep,
    file: Annotated[UploadFile, File()],
    request: Request,
    settings: SettingsDep,
) -> dict[str, object]:
    """Preview only. Parser runs in a bounded external process."""
    key = preview_key(request, settings)
    if file.size is not None and file.size > MAX_FILE_BYTES:
        raise UnprocessableError("Arquivo acima de 2 MB", code="CV_SIZE")
    payload = await file.read(MAX_FILE_BYTES + 1)
    await file.close()
    if len(payload) > MAX_FILE_BYTES:
        raise UnprocessableError("Arquivo acima de 2 MB", code="CV_SIZE")
    preview = await run_in_threadpool(parse_in_worker, file.filename or "", payload)
    preview["preview_ticket"] = sign_preview(preview, user_id=str(user.id), key=key)
    return preview


@router.post(
    "/confirm",
    response_model=ConfirmResult,
    status_code=201,
    responses=error_responses(401, 409, 422, 503),
)
def confirm_resume(
    data: ImportConfirmation,
    user: CurrentUserDep,
    session: SessionDep,
    request: Request,
    settings: SettingsDep,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=128)],
) -> ConfirmResult:
    key = preview_key(request, settings)
    return confirm_import(
        session,
        user_id=user.id,
        confirmation=data,
        key=key,
        idempotency_key=idempotency_key,
    )
