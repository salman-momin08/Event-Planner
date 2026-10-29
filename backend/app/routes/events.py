from __future__ import annotations

import json
import sqlite3

from fastapi import APIRouter, Depends, Query, Response

from ..context import Context
from ..deps import get_ctx, owned_event, require_user
from ..errors import ApiError
from ..schemas import EventIn, EventPatch
from ..services import budget, events, tasks, vendors
from ..services.export import CSV_SECTIONS, export_csv, export_json

router = APIRouter(prefix="/events")


@router.get("")
async def list_events(
    limit: int = Query(50), offset: int = Query(0), ctx: Context = Depends(get_ctx), user: dict = Depends(require_user)
):
    return events.list_events(ctx, user["id"], min(max(limit, 1), 200), max(offset, 0))


@router.post("", status_code=201)
async def create_event(body: EventIn, ctx: Context = Depends(get_ctx), user: dict = Depends(require_user)):
    return events.create_event(ctx, user["id"], body)


@router.get("/{event_id:int}")
async def get_event(event: sqlite3.Row = Depends(owned_event)):
    return events.to_event(event)


@router.patch("/{event_id:int}")
async def patch_event(
    body: EventPatch, event: sqlite3.Row = Depends(owned_event), ctx: Context = Depends(get_ctx), user: dict = Depends(require_user)
):
    return events.update_event(ctx, user["id"], event["id"], body)


@router.delete("/{event_id:int}", status_code=204)
async def delete_event(event: sqlite3.Row = Depends(owned_event), ctx: Context = Depends(get_ctx), user: dict = Depends(require_user)):
    events.delete_event(ctx, user["id"], event["id"])
    return Response(status_code=204)


@router.get("/{event_id:int}/summary")
async def summary(event: sqlite3.Row = Depends(owned_event), ctx: Context = Depends(get_ctx)):
    return {
        "budget": budget.summarize(ctx, event),
        "tasks": tasks.task_stats(ctx, event["id"]),
        "vendors": vendors.vendor_stats(ctx, event["id"]),
    }


@router.get("/{event_id:int}/export")
async def export(
    format: str = Query("json"),
    section: str | None = Query(None),
    event: sqlite3.Row = Depends(owned_event),
    ctx: Context = Depends(get_ctx),
):
    base = f"event-{event['id']}"
    if format == "json":
        return Response(
            json.dumps(export_json(ctx, event), indent=2),
            media_type="application/json; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{base}.json"', "Cache-Control": "no-store"},
        )
    if format == "csv" and section in CSV_SECTIONS:
        return Response(
            export_csv(ctx, event, section),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{base}-{section}.csv"', "Cache-Control": "no-store"},
        )
    raise ApiError(
        400, "validation_error", "Invalid export options",
        {"format": "Use format=json, or format=csv with section=tasks|expenses|vendors"},
    )
