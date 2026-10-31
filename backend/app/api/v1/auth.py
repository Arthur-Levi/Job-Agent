"""D2-E1 real user identity API. All payloads synthetic in acceptance tests."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field

from app.api.deps import SessionDep, SettingsDep, get_database
from app.db.session import Database
from app.services import account_lifecycle as lifecycle
from app.services import auth
from app.services.auth_rate_limit import (
    RateLimitExceeded,
    RateLimitUnavailable,
    consume,
)
from app.services.email_delivery import MemoryMailer

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class EmailRequestIn(BaseModel):
    email: EmailStr


class ActionTokenIn(BaseModel):
    token: str = Field(min_length=32, max_length=256)


class ResetPasswordIn(ActionTokenIn):
    new_password: str = Field(min_length=12, max_length=128)


class MessageOut(BaseModel):
    message: str


class UserOut(BaseModel):
    id: str
    name: str
    email: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


def bearer(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(401, "Autenticação necessária")
    kind, sep, token = authorization.partition(" ")
    if not sep or kind.lower() != "bearer" or not token:
        raise HTTPException(401, "Autenticação necessária")
    return token


@router.post("/register", status_code=201, response_model=UserOut)
def register(
    payload: RegisterIn, session: SessionDep, settings: SettingsDep, request: Request
) -> UserOut | JSONResponse:
    try:
        user = auth.register(
            session, name=payload.name, email=payload.email, password=payload.password
        )
    except auth.DuplicateAccount:
        if not settings.registration_privacy_enabled:
            raise HTTPException(409, "Conta já cadastrada") from None
        # Similar Argon2 workload; neither account identifiers nor existence escape.
        auth.PASSWORD_HASHER.hash(payload.password)
        return JSONResponse(
            status_code=202,
            content={"message": "Seus dados foram recebidos. Se puder concluir, entre na conta."},
        )
    if settings.identity_lifecycle_enabled:
        mailer = _mailer(request, settings)
        lifecycle.dispatch(
            session,
            email=payload.email,
            purpose=lifecycle.VERIFY,
            mailer=mailer,
            frontend_url=settings.public_frontend_url,
        )
    if settings.registration_privacy_enabled:
        return JSONResponse(
            status_code=202,
            content={"message": "Seus dados foram recebidos. Se puder concluir, entre na conta."},
        )
    return UserOut(id=str(user.id), name=user.name, email=user.email or "")


@router.post("/login", response_model=TokenOut)
def login(
    payload: LoginIn,
    session: SessionDep,
    settings: SettingsDep,
    database: Annotated[Database, Depends(get_database)],
) -> TokenOut:
    if settings.auth_rate_limit_enabled:
        try:
            consume(
                database,
                settings,
                kind="login_account",
                identity=payload.email.strip().casefold(),
                maximum=settings.auth_login_account_max,
            )
        except RateLimitExceeded as exc:
            raise HTTPException(
                429,
                "Too many requests. Try again later.",
                headers={"Retry-After": str(exc.retry_after)},
            ) from None
        except RateLimitUnavailable:
            raise HTTPException(503, "Service temporarily unavailable") from None
    try:
        token = auth.login(
            session,
            email=payload.email,
            password=payload.password,
            require_verified=settings.identity_lifecycle_enabled,
        )
    except auth.InvalidCredentials:
        raise HTTPException(401, "Credenciais inválidas") from None
    return TokenOut(access_token=token)


@router.get("/me", response_model=UserOut)
def me(session: SessionDep, authorization: str | None = Header(default=None)) -> UserOut:
    user = auth.current(session, bearer(authorization))
    if user is None:
        raise HTTPException(401, "Sessão inválida")
    return UserOut(id=str(user.id), name=user.name, email=user.email or "")


@router.post("/logout", status_code=204)
def logout(session: SessionDep, authorization: str | None = Header(default=None)) -> None:
    token = bearer(authorization)
    if auth.current(session, token) is None:
        raise HTTPException(401, "Sessão inválida")
    auth.logout(session, token)


def _mailer(request: Request, settings: SettingsDep) -> MemoryMailer:
    if not settings.identity_lifecycle_enabled:
        raise HTTPException(503, "Account verification not configured")
    mailer = getattr(request.app.state, "mailer", None)
    if not isinstance(mailer, MemoryMailer):
        raise HTTPException(503, "Email delivery unavailable")
    return mailer


def _limited_email_request(
    database: Database, settings: SettingsDep, *, email: str, purpose: str
) -> None:
    if not settings.auth_rate_limit_enabled:
        return
    try:
        consume(
            database,
            settings,
            kind=f"identity_email_{purpose}",
            identity=email.strip().casefold(),
            maximum=3,
        )
    except RateLimitExceeded as exc:
        raise HTTPException(
            429,
            "Too many requests. Try again later.",
            headers={"Retry-After": str(exc.retry_after)},
        ) from None
    except RateLimitUnavailable:
        raise HTTPException(503, "Service temporarily unavailable") from None


@router.post("/request-verification", status_code=202, response_model=MessageOut)
def request_verification(
    payload: EmailRequestIn,
    session: SessionDep,
    settings: SettingsDep,
    request: Request,
    database: Annotated[Database, Depends(get_database)],
) -> MessageOut:
    mailer = _mailer(request, settings)
    _limited_email_request(database, settings, email=payload.email, purpose="verify")
    lifecycle.dispatch(
        session,
        email=payload.email,
        purpose=lifecycle.VERIFY,
        mailer=mailer,
        frontend_url=settings.public_frontend_url,
    )
    return MessageOut(message="Se existir uma conta elegível, enviaremos instruções.")


@router.post("/verify-email", status_code=204)
def verify_email(
    payload: ActionTokenIn, session: SessionDep, settings: SettingsDep, request: Request
) -> None:
    _mailer(request, settings)
    try:
        lifecycle.consume(session, token=payload.token, purpose=lifecycle.VERIFY)
    except lifecycle.InvalidActionToken:
        raise HTTPException(400, "Token inválido ou expirado") from None


@router.post("/request-password-reset", status_code=202, response_model=MessageOut)
def request_password_reset(
    payload: EmailRequestIn,
    session: SessionDep,
    settings: SettingsDep,
    request: Request,
    database: Annotated[Database, Depends(get_database)],
) -> MessageOut:
    mailer = _mailer(request, settings)
    _limited_email_request(database, settings, email=payload.email, purpose="reset")
    lifecycle.dispatch(
        session,
        email=payload.email,
        purpose=lifecycle.RESET,
        mailer=mailer,
        frontend_url=settings.public_frontend_url,
    )
    return MessageOut(message="Se existir uma conta elegível, enviaremos instruções.")


@router.post("/reset-password", status_code=204)
def reset_password(
    payload: ResetPasswordIn, session: SessionDep, settings: SettingsDep, request: Request
) -> None:
    _mailer(request, settings)
    try:
        lifecycle.consume(
            session,
            token=payload.token,
            purpose=lifecycle.RESET,
            new_password=payload.new_password,
        )
    except lifecycle.InvalidActionToken:
        raise HTTPException(400, "Token inválido ou expirado") from None
