import logging
import secrets
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from agent.engine_client import LiveEngine
from agent.orchestrator import Orchestrator
from backend.app.auth import router as auth_router
from backend.app.database import Database
from backend.app.errors import ApiError, AuthenticationError, error_response
from backend.app.field_checks import router as field_checks_router
from backend.app.logging_setup import configure_logging
from backend.app.questions import router as questions_router
from backend.app.settings import Settings
from backend.app.support_requests import router as support_requests_router

settings = Settings.from_environment()
configure_logging(settings.log_level)
logger = logging.getLogger("backend.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.environment in {"production", "prod"}:
        if not settings.jwt_secret or len(settings.jwt_secret) < 32:
            raise RuntimeError(
                "BACKEND_JWT_SECRET must contain at least 32 characters in production"
            )
    database = Database(settings.database_path)
    database.initialize()
    app.state.database = database
    app.state.jwt_secret = settings.jwt_secret or secrets.token_urlsafe(32)
    try:
        engine = LiveEngine()
        app.state.question_orchestrators = {
            mode: Orchestrator(engine, mode=mode) for mode in ("admin", "citizen")
        }
        yield
    finally:
        del app.state.database
        del app.state.jwt_secret
        if hasattr(app.state, "question_orchestrators"):
            del app.state.question_orchestrators


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(auth_router)
app.include_router(questions_router)
app.include_router(support_requests_router)
app.include_router(field_checks_router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid4())
    request.state.request_id = request_id
    started_at = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        logger.info(
            "request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
            },
        )


@app.exception_handler(ApiError)
async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
    return error_response(
        request, exc.status_code, exc.code, exc.message, exc.details
    )


@app.exception_handler(AuthenticationError)
async def handle_authentication_error(
    request: Request, exc: AuthenticationError
) -> JSONResponse:
    response = error_response(request, exc.status_code, exc.code, exc.message)
    if exc.status_code == 401:
        response.headers["WWW-Authenticate"] = "Bearer"
    return response


@app.exception_handler(StarletteHTTPException)
async def handle_http_error(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return error_response(request, exc.status_code, "http_error", message)


@app.exception_handler(RequestValidationError)
async def handle_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = [
        {"location": error["loc"], "message": error["msg"], "type": error["type"]}
        for error in exc.errors()
    ]
    return error_response(
        request, 422, "validation_error", "Request validation failed", details
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "unhandled application error",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "error_type": type(exc).__name__,
        },
    )
    return error_response(
        request, 500, "internal_server_error", "Internal server error"
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
