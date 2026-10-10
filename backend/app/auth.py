from datetime import datetime, timedelta, timezone
import sqlite3

import jwt
from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pwdlib import PasswordHash
from starlette.concurrency import run_in_threadpool

from backend.app.errors import AuthenticationError

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
bearer = HTTPBearer(auto_error=False)
password_hash = PasswordHash.recommended()
TOKEN_LIFETIME = timedelta(hours=1)
DUMMY_PASSWORD_HASH = password_hash.hash("fixed-invalid-login-placeholder")


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError(401, "unauthorized", "Authentication required")
    try:
        claims = jwt.decode(
            credentials.credentials,
            request.app.state.jwt_secret,
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )
        user_id = int(claims["sub"])
    except (jwt.InvalidTokenError, TypeError, ValueError):
        raise AuthenticationError(401, "unauthorized", "Authentication required") from None
    user = request.app.state.database.get_user_by_id(user_id)
    if user is None:
        raise AuthenticationError(401, "unauthorized", "Authentication required")
    return user


def require_roles(*roles: str):
    def dependency(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in roles:
            raise AuthenticationError(403, "forbidden", "Insufficient permissions")
        return user

    return dependency


def issue_token(user: dict, secret: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(user["id"]),
            "iat": now,
            "exp": now + TOKEN_LIFETIME,
        },
        secret,
        algorithm="HS256",
    )


@router.post("/register", status_code=201)
async def register(payload: UserCreate, request: Request) -> dict:
    encoded_password = await run_in_threadpool(password_hash.hash, payload.password)
    try:
        user = await run_in_threadpool(
            request.app.state.database.create_user,
            str(payload.email),
            encoded_password,
            "citizen",
        )
    except sqlite3.IntegrityError:
        raise AuthenticationError(
            409, "account_unavailable", "Unable to create account"
        ) from None
    return user


@router.post("/login")
async def login(payload: LoginRequest, request: Request) -> dict:
    user = await run_in_threadpool(
        request.app.state.database.get_user_by_email, str(payload.email)
    )
    encoded_password = user["password_hash"] if user is not None else DUMMY_PASSWORD_HASH
    valid = await run_in_threadpool(
        password_hash.verify, payload.password, encoded_password
    )
    if user is None or not valid:
        raise AuthenticationError(401, "invalid_credentials", "Invalid email or password")
    return {
        "access_token": issue_token(user, request.app.state.jwt_secret),
        "token_type": "bearer",
        "expires_in": int(TOKEN_LIFETIME.total_seconds()),
        "user": {key: user[key] for key in ("id", "email", "role")},
    }
