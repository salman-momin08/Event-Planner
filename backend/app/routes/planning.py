from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Response

from ..context import Context
from ..deps import get_ctx, owned_event
from ..schemas import (
    CategoryIn,
    CategoryPatch,
    ExpenseIn,
    ExpensePatch,
    TaskIn,
    TaskPatch,
    VendorIn,
    VendorPatch,
)
from ..services import budget, tasks, templates, vendors

router = APIRouter(prefix="/events/{event_id:int}")


# --- budget ---
@router.get("/budget-categories")
async def list_categories(event: sqlite3.Row = Depends(owned_event), ctx: Context = Depends(get_ctx)):
    return budget.list_categories(ctx, event["id"])


@router.post("/budget-categories", status_code=201)
async def create_category(body: CategoryIn, event: sqlite3.Row = Depends(owned_event), ctx: Context = Depends(get_ctx)):
    return budget.create_category(ctx, event["id"], body)


@router.patch("/budget-categories/{category_id:int}")
async def patch_category(category_id: int, body: CategoryPatch, event: sqlite3.Row = Depends(owned_event), ctx: Context = Depends(get_ctx)):
    return budget.update_category(ctx, event["id"], category_id, body)


@router.delete("/budget-categories/{category_id:int}", status_code=204)
async def delete_category(category_id: int, event: sqlite3.Row = Depends(owned_event), ctx: Context = Depends(get_ctx)):
    budget.delete_category(ctx, event["id"], category_id)
    return Response(status_code=204)


@router.get("/expenses")
async def list_expenses(event: sqlite3.Row = Depends(owned_event), ctx: Context = Depends(get_ctx)):
    return budget.list_expenses(ctx, event["id"])


@router.post("/expenses", status_code=201)
async def create_expense(body: ExpenseIn, event: sqlite3.Row = Depends(owned_event), ctx: Context = Depends(get_ctx)):
    return budget.create_expense(ctx, event["id"], body)


@router.patch("/expenses/{expense_id:int}")
async def patch_expense(expense_id: int, body: ExpensePatch, event: sqlite3.Row = Depends(owned_event), ctx: Context = Depends(get_ctx)):
    return budget.update_expense(ctx, event["id"], expense_id, body)


@router.delete("/expenses/{expense_id:int}", status_code=204)
async def delete_expense(expense_id: int, event: sqlite3.Row = Depends(owned_event), ctx: Context = Depends(get_ctx)):
    budget.delete_expense(ctx, event["id"], expense_id)
    return Response(status_code=204)


# --- tasks & timeline ---
@router.get("/tasks")
async def list_tasks(event: sqlite3.Row = Depends(owned_event), ctx: Context = Depends(get_ctx)):
    return tasks.list_tasks(ctx, event["id"])


@router.post("/tasks", status_code=201)
async def create_task(body: TaskIn, event: sqlite3.Row = Depends(owned_event), ctx: Context = Depends(get_ctx)):
    return tasks.create_task(ctx, event["id"], body)


@router.patch("/tasks/{task_id:int}")
async def patch_task(task_id: int, body: TaskPatch, event: sqlite3.Row = Depends(owned_event), ctx: Context = Depends(get_ctx)):
    return tasks.update_task(ctx, event["id"], task_id, body)


@router.delete("/tasks/{task_id:int}", status_code=204)
async def delete_task(task_id: int, event: sqlite3.Row = Depends(owned_event), ctx: Context = Depends(get_ctx)):
    tasks.delete_task(ctx, event["id"], task_id)
    return Response(status_code=204)


@router.get("/timeline")
async def get_timeline(event: sqlite3.Row = Depends(owned_event), ctx: Context = Depends(get_ctx)):
    return tasks.timeline(ctx, event["id"])


@router.post("/timeline/generate-template")
async def generate_template(event: sqlite3.Row = Depends(owned_event), ctx: Context = Depends(get_ctx)):
    return templates.generate_timeline(ctx, event)


# --- vendors ---
@router.get("/vendors")
async def list_vendors(event: sqlite3.Row = Depends(owned_event), ctx: Context = Depends(get_ctx)):
    return vendors.list_vendors(ctx, event["id"])


@router.post("/vendors", status_code=201)
async def create_vendor(body: VendorIn, event: sqlite3.Row = Depends(owned_event), ctx: Context = Depends(get_ctx)):
    return vendors.create_vendor(ctx, event["id"], body)


@router.patch("/vendors/{vendor_id:int}")
async def patch_vendor(vendor_id: int, body: VendorPatch, event: sqlite3.Row = Depends(owned_event), ctx: Context = Depends(get_ctx)):
    return vendors.update_vendor(ctx, event["id"], vendor_id, body)


@router.delete("/vendors/{vendor_id:int}", status_code=204)
async def delete_vendor(vendor_id: int, event: sqlite3.Row = Depends(owned_event), ctx: Context = Depends(get_ctx)):
    vendors.delete_vendor(ctx, event["id"], vendor_id)
    return Response(status_code=204)
