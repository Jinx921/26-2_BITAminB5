from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.concurrency import run_in_threadpool

router = APIRouter(prefix="/api/v1/support-requests", tags=["support requests"])


class SupportRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    facility_id: str = Field(min_length=1, max_length=200)
    requester_name: str = Field(min_length=1, max_length=200)
    contact: str = Field(min_length=1, max_length=500)
    requested_at: datetime
    request_type: Literal["companion", "mobility"]
    note: str = Field(default="", max_length=5000)

    @field_validator("facility_id", "requester_name", "contact")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_support_request(
    payload: SupportRequestCreate, request: Request
) -> dict:
    values = payload.model_dump(mode="json")
    return await run_in_threadpool(
        request.app.state.database.create_support_request, values
    )


@router.get("")
async def list_support_requests(
    request: Request,
    status_filter: str | None = Query(
        default=None, alias="status", min_length=1
    ),
) -> list[dict]:
    return await run_in_threadpool(
        request.app.state.database.list_support_requests, status_filter
    )


@router.get("/{request_id}")
async def get_support_request(request_id: int, request: Request) -> dict:
    support_request = await run_in_threadpool(
        request.app.state.database.get_support_request, request_id
    )
    if support_request is None:
        raise HTTPException(status_code=404, detail="Support request not found")
    return support_request
