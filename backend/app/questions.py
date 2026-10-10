from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from starlette.concurrency import run_in_threadpool


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

    @model_validator(mode="after")
    def location_is_citizen_only(self) -> "QuestionRequest":
        if self.mode == "admin" and self.location is not None:
            raise ValueError("location is only supported in citizen mode")
        return self


router = APIRouter(prefix="/api/v1", tags=["questions"])


@router.post("/questions")
async def ask_question(
    payload: QuestionRequest, request: Request
) -> dict:
    orchestrator = request.app.state.question_orchestrators[payload.mode]
    location = payload.location.model_dump() if payload.location is not None else None
    screen, _turn = await run_in_threadpool(
        orchestrator.ask, payload.question, location
    )
    return screen["display"]
