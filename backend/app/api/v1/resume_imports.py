"""D2-E2.C: auth-protected, non-persistent CV preview."""

from typing import Annotated

from fastapi import APIRouter, File, UploadFile

from app.api.deps import CurrentUserDep
from app.core.errors import UnprocessableError, error_responses
from app.services.resume_preview import MAX_FILE_BYTES, build_preview

router = APIRouter(prefix="/resume-imports", tags=["resume-imports"])


@router.post("/preview", responses=error_responses(401, 413, 422))
async def preview_resume(
    user: CurrentUserDep, file: Annotated[UploadFile, File()]
) -> dict[str, object]:
    """No database writes or raw-document persistence. user dependency gates access."""
    _ = user.id
    if file.size is not None and file.size > MAX_FILE_BYTES:
        raise UnprocessableError("Arquivo acima de 2 MB", code="CV_SIZE")
    payload = await file.read(MAX_FILE_BYTES + 1)
    await file.close()
    if len(payload) > MAX_FILE_BYTES:
        raise UnprocessableError("Arquivo acima de 2 MB", code="CV_SIZE")
    return build_preview(file.filename or "", payload)
