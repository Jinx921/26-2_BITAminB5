from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    field_validator,
)
from starlette.concurrency import run_in_threadpool

from backend.app.auth import require_roles

router = APIRouter(prefix="/api/v1/field-check-list", tags=["field check lists"])

NonEmptyText = Annotated[StrictStr, Field(min_length=1)]


class FieldCheckListCell(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Annotated[StrictStr, Field(min_length=1, max_length=200)]
    lat: StrictFloat = Field(ge=-90, le=90)
    lon: StrictFloat = Field(ge=-180, le=180)
    emd_name: NonEmptyText
    level: NonEmptyText
    questions: list[NonEmptyText]
    order: StrictInt = Field(ge=1)
    highlight: StrictBool

    @field_validator("id", "emd_name", "level")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value


class FieldCheckList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    region: StrictStr | None
    headline: NonEmptyText
    created_at: Annotated[StrictStr, Field(min_length=1)]
    cells: list[FieldCheckListCell] = Field(min_length=1)

    @field_validator("headline")
    @classmethod
    def headline_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("headline must not be blank")
        return value

    @field_validator("created_at")
    @classmethod
    def created_at_must_be_timezone_aware_iso_datetime(cls, value: str) -> str:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError("created_at must be an ISO 8601 datetime") from None
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("created_at must include a timezone")
        return value


@router.get("", response_model=FieldCheckList | None)
async def get_field_check_list(
    request: Request,
    user: dict = Depends(require_roles("field_worker")),
) -> dict[str, Any] | None:
    return await run_in_threadpool(
        request.app.state.database.get_field_check_list, user["id"]
    )


@router.put("", response_model=FieldCheckList)
async def save_field_check_list(
    payload: FieldCheckList,
    request: Request,
    user: dict = Depends(require_roles("field_worker")),
) -> dict[str, Any]:
    return await run_in_threadpool(
        request.app.state.database.save_field_check_list,
        user["id"],
        payload.model_dump(mode="json"),
    )
