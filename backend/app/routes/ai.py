from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from ..ai import plans
from ..context import Context
from ..deps import get_ctx, owned_event, require_user
from ..schemas import PlanApplyIn, PlanRequest

router = APIRouter()


@router.get("/ai/status")
async def ai_status(ctx: Context = Depends(get_ctx), user: dict = Depends(require_user)):
    return {"available": ctx.ai.available}


@router.get("/events/{event_id:int}/ai/plans")
async def list_plans(event: sqlite3.Row = Depends(owned_event), ctx: Context = Depends(get_ctx)):
    return plans.list_plans(ctx, event["id"])


@router.post("/events/{event_id:int}/ai/plans", status_code=201)
async def create_plan(
    body: PlanRequest | None = None,
    event: sqlite3.Row = Depends(owned_event),
    ctx: Context = Depends(get_ctx),
    user: dict = Depends(require_user),
):
    return await plans.create_draft(ctx, user, event, body or PlanRequest())


@router.get("/events/{event_id:int}/ai/plans/{plan_id:int}")
async def get_plan(plan_id: int, event: sqlite3.Row = Depends(owned_event), ctx: Context = Depends(get_ctx)):
    return plans.get_plan(ctx, event["id"], plan_id)


@router.post("/events/{event_id:int}/ai/plans/{plan_id:int}/apply")
async def apply_plan(
    plan_id: int,
    body: PlanApplyIn | None = None,
    event: sqlite3.Row = Depends(owned_event),
    ctx: Context = Depends(get_ctx),
):
    return plans.apply_plan(ctx, event, plan_id, body)


@router.post("/events/{event_id:int}/ai/plans/{plan_id:int}/discard")
async def discard_plan(plan_id: int, event: sqlite3.Row = Depends(owned_event), ctx: Context = Depends(get_ctx)):
    return plans.discard_plan(ctx, event["id"], plan_id)
