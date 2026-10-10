import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.errors import ApiError, error_response
from backend.app.logging_setup import configure_logging
from backend.app.settings import Settings

settings = Settings.from_environment()
configure_logging(settings.log_level)
logger = logging.getLogger("backend.api")

app = FastAPI(title=settings.app_name)


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
    logger.exception(
        "unhandled application error",
        extra={"request_id": getattr(request.state, "request_id", None)},
    )
    return error_response(
        request, 500, "internal_server_error", "Internal server error"
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
