"""D2-E1 real user identity API. All payloads synthetic in acceptance tests."""
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, EmailStr, Field

from app.api.deps import SessionDep
from app.services import auth

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
def login(payload: LoginIn, session: SessionDep) -> TokenOut:
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
