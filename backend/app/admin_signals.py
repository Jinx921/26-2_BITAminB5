from fastapi import APIRouter, Depends, Request
from starlette.concurrency import run_in_threadpool

from backend.app.auth import require_roles

router = APIRouter(prefix="/api/v1/admin", tags=["admin operations signals"])
MINIMUM_DEMAND_GROUP_SIZE = 3


@router.get("/demand-signals")
async def demand_signals(
    request: Request,
    _admin: dict = Depends(require_roles("admin")),
) -> list[dict]:
    return await run_in_threadpool(
        request.app.state.database.demand_signals,
        MINIMUM_DEMAND_GROUP_SIZE,
    )


@router.get("/field-feedback-summary")
async def field_feedback_summary(
    request: Request,
    _admin: dict = Depends(require_roles("admin")),
) -> list[dict]:
    return await run_in_threadpool(
        request.app.state.database.field_feedback_summary
    )
