from datetime import datetime
from typing import Any

from fastapi import APIRouter, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.concurrency import run_in_threadpool

router = APIRouter(prefix="/api/v1/field-checks", tags=["field checks"])


class FieldCheckCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cell_id: str = Field(min_length=1, max_length=200)
    checklist: dict[str, Any]
    checked_at: datetime
    note: str = Field(default="", max_length=5000)

    @field_validator("cell_id")
    @classmethod
    def cell_id_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("cell_id must not be blank")
        return value


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_field_check(payload: FieldCheckCreate, request: Request) -> dict:
    values = payload.model_dump(mode="json")
    return await run_in_threadpool(
        request.app.state.database.create_field_check, values
    )


@router.get("")
async def list_field_checks(
    request: Request, cell_id: str = Query(min_length=1)
) -> list[dict]:
    return await run_in_threadpool(
        request.app.state.database.list_field_checks, cell_id
    )
