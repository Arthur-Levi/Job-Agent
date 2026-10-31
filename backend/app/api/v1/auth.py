"""D2-E1 real user identity API. All payloads synthetic in acceptance tests."""
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, EmailStr, Field

from app.api.deps import SessionDep, SettingsDep, get_database
from app.db.session import Database
from app.services import auth
from app.services.auth_rate_limit import (
    RateLimitExceeded,
    RateLimitUnavailable,
    consume,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


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
def register(payload: RegisterIn, session: SessionDep) -> UserOut:
    try:
        user = auth.register(session, name=payload.name, email=payload.email, password=payload.password)
    except auth.DuplicateAccount:
        raise HTTPException(409, "Conta já cadastrada") from None
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
                database, settings, kind="login_account",
                identity=payload.email.strip().casefold(),
                maximum=settings.auth_login_account_max,
            )
        except RateLimitExceeded as exc:
            raise HTTPException(
                429, "Too many requests. Try again later.",
                headers={"Retry-After": str(exc.retry_after)},
            ) from None
        except RateLimitUnavailable:
            raise HTTPException(503, "Service temporarily unavailable") from None
    try:
        token = auth.login(session, email=payload.email, password=payload.password)
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
