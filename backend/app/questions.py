import time
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.concurrency import run_in_threadpool

from backend.app.auth import require_roles
from backend.app.errors import ApiError


class QuestionLocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class QuestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["admin", "citizen"]
    question: str = Field(min_length=1)
    location: QuestionLocation | None = None

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("question must not be blank")
        return value

router = APIRouter(prefix="/api/v1", tags=["questions"])


@router.post("/questions")
async def ask_question(
    payload: QuestionRequest,
    request: Request,
    user: dict = Depends(require_roles("admin", "citizen")),
) -> dict:
    if user["role"] == "admin" and payload.location is not None:
        raise ApiError(
            422,
            "validation_error",
            "Request validation failed",
            [
                {
                    "location": ["body", "location"],
                    "message": "location is only supported for citizen accounts",
                    "type": "value_error",
                }
            ],
        )
    execution_gate = request.app.state.question_execution_gate
    if not execution_gate.try_enter():
        raise ApiError(
            503,
            "question_capacity_exceeded",
            "Question service is temporarily busy",
            headers={"Retry-After": "1"},
        )

    try:
        user_id = int(user["id"])
        retry_after = await run_in_threadpool(
            request.app.state.database.record_question_request,
            user_id,
            time.time(),
            request.app.state.question_rate_window_seconds,
            request.app.state.question_rate_limits[user["role"]],
        )
        if retry_after is not None:
            raise ApiError(
                429,
                "rate_limit_exceeded",
                "Question request limit exceeded",
                headers={"Retry-After": str(retry_after)},
            )

        orchestrator = request.app.state.question_orchestrators[user["role"]]
        location = (
            payload.location.model_dump() if payload.location is not None else None
        )
        screen, _turn = await run_in_threadpool(
            orchestrator.ask, payload.question, location
        )
        return screen["display"]
    finally:
        execution_gate.leave()
