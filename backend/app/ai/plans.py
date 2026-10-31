from __future__ import annotations

import json
import sqlite3
import time

from ..context import Context
from ..dates import add_days, to_date_string
from ..db import transaction
from ..errors import ApiError, bad_request, conflict, limit_reached, not_found
from ..money import percent_to_cents
from ..schemas import PlanApplyIn, PlanRequest
from ..security import enforce
from ..services.auth import record_security_event
from ..services.budget import LIMITS as BUDGET_LIMITS
from ..services.tasks import LIMITS as TASK_LIMITS
from ..services.vendors import MAX_VENDORS
from .graph import run_plan_graph
from .guardrails import inspect_ai_input
from .prompts import PROMPT_VERSION, build_context, context_json

MAX_PLANS_PER_EVENT = 50


def _plan(r: sqlite3.Row) -> dict:
    plan_data = json.loads(r["plan_json"])
    for t in plan_data.get("tasks", []):
        d = int(t.get("daysBeforeEvent", 0))
        if d > 45:
            t["daysBeforeEvent"] = max(1, min(45, round(d / 10)))
    return {
        "id": r["id"],
        "eventId": r["event_id"],
        "parentId": r["parent_id"],
        "status": r["status"],
        "instruction": r["instruction"],
        "preferences": r["preferences"],
        "plan": plan_data,
        "promptVersion": r["prompt_version"],
        "model": r["model"],
        "createdAt": r["created_at"],
    }


def _row(ctx: Context, event_id: int, plan_id: int) -> sqlite3.Row:
    row = ctx.db.execute("SELECT * FROM ai_plan_versions WHERE id = ? AND event_id = ?", (plan_id, event_id)).fetchone()
    if row is None:
        raise not_found("Plan")
    return row


def list_plans(ctx: Context, event_id: int) -> list[dict]:
    rows = ctx.db.execute("SELECT * FROM ai_plan_versions WHERE event_id = ? ORDER BY id DESC", (event_id,)).fetchall()
    return [_plan(r) for r in rows]


def get_plan(ctx: Context, event_id: int, plan_id: int) -> dict:
    return _plan(_row(ctx, event_id, plan_id))


async def create_draft(ctx: Context, user: dict, event: sqlite3.Row, body: PlanRequest) -> dict:
    """Creates an inert draft. Only `ai_plan_versions` is written, so failures leave the plan untouched."""
    if not ctx.ai.available:
        raise ApiError(
            503, "ai_unavailable",
            "The AI assistant is not configured. You can still plan manually or generate a template timeline.",
        )
    if body.instruction and body.parentId is None:
        raise bad_request({"parentId": "A revision instruction requires parentId"})

    inspect_ai_input(
        ctx,
        user["id"],
        {"preferences": body.preferences, "instruction": body.instruction},
    )

    previous_plan = json.loads(_row(ctx, event["id"], body.parentId)["plan_json"]) if body.parentId else None
    n = ctx.db.execute("SELECT COUNT(*) AS n FROM ai_plan_versions WHERE event_id = ?", (event["id"],)).fetchone()["n"]
    if n >= MAX_PLANS_PER_EVENT:
        raise limit_reached(f"An event can keep at most {MAX_PLANS_PER_EVENT} AI drafts; discard some first")

    try:
        enforce(ctx.limiters["ai_minute"], f"ai:{user['id']}", "AI requests are limited to a few per minute")
        enforce(ctx.limiters["ai_daily"], f"ai:{user['id']}", "Daily AI request limit reached")
    except ApiError as err:
        if err.status == 429:
            record_security_event(ctx, user["id"], "ai_rate_limited", None)
            ctx.logger.warn("ai_rate_limited", userId=user["id"])
        raise

    started = time.monotonic()
    outcome = "ok"
    try:
        context = build_context(
            event, to_date_string(ctx.clock()), body.preferences, body.instruction, previous_plan
        )
        plan = await run_plan_graph(ctx.ai.graph, context_json(context))
        cur = ctx.db.execute(
            """INSERT INTO ai_plan_versions (event_id, parent_id, status, instruction, preferences, plan_json,
                                             prompt_version, model, created_at)
               VALUES (?, ?, 'draft', ?, ?, ?, ?, ?, ?)""",
            (event["id"], body.parentId, body.instruction, body.preferences, json.dumps(plan),
             PROMPT_VERSION, ctx.ai.model_label, ctx.clock().isoformat()),
        )
        return get_plan(ctx, event["id"], int(cur.lastrowid))
    except ApiError as err:
        outcome = err.code
        raise
    except Exception:
        outcome = "error"
        raise
    finally:
        ctx.logger.info(
            "ai", userId=user["id"], outcome=outcome, latencyMs=round((time.monotonic() - started) * 1000),
            model=ctx.ai.model_label,
        )


def discard_plan(ctx: Context, event_id: int, plan_id: int) -> dict:
    row = _row(ctx, event_id, plan_id)
    if row["status"] != "draft":
        raise conflict("Only drafts can be discarded", "not_a_draft")
    ctx.db.execute("UPDATE ai_plan_versions SET status = 'discarded' WHERE id = ? AND event_id = ?", (plan_id, event_id))
    return get_plan(ctx, event_id, plan_id)


def _select(plan: dict, body: PlanApplyIn | None) -> tuple[list[dict], list[dict]]:
    """Narrows the plan to the user's selected categories/tasks (all of them when unspecified)."""
    cats = plan["budgetAllocations"]
    tasks = plan["tasks"]
    if body is not None and body.categories is not None:
        allowed = {c.lower() for c in body.categories}
        cats = [b for b in cats if b["category"].lower() in allowed]
    if body is not None and body.tasks is not None:
        allowed = {t.lower() for t in body.tasks}
        tasks = [t for t in tasks if t["title"].lower() in allowed]
    return cats, tasks


def _plan_vendors(ctx: Context, event_id: int, plan: dict) -> tuple[list[dict], int]:
    """Builds the vendor shortlists to create, de-duplicated against existing vendor names/categories."""
    vendor_rows = ctx.db.execute("SELECT name, category FROM vendors WHERE event_id = ?", (event_id,)).fetchall()
    existing_cats = {r["category"].lower() for r in vendor_rows if r["category"]}
    existing_names = {r["name"].lower() for r in vendor_rows}
    new_vendors: list[dict] = []
    for v in plan.get("vendorSuggestions", []):
        v_cat = v["category"].strip()
        v_name = f"{v_cat} (shortlist)"[:80]
        if v_cat.lower() not in existing_cats and v_name.lower() not in existing_names:
            new_vendors.append({"name": v_name, "category": v_cat, "contact": v["guidance"]})
            existing_cats.add(v_cat.lower())
            existing_names.add(v_name.lower())
    return new_vendors, len(vendor_rows)


def _insert_categories(ctx: Context, event_id: int, budget_cents: int, new_cats: list[dict]) -> None:
    for b in new_cats:
        ctx.db.execute(
            "INSERT INTO budget_categories (event_id, name, planned_cents) VALUES (?, ?, ?)",
            (event_id, b["category"], percent_to_cents(budget_cents, b["percent"])),
        )


def _insert_tasks(
    ctx: Context, event_id: int, event_date: str, new_tasks: list[dict], task_id_by_title: dict[str, int], ts: str
) -> None:
    """Inserts tasks, then wires dependencies once every new task has an id (prerequisites may appear later)."""
    pending_deps: list[tuple[int, list[str]]] = []
    for t in new_tasks:
        cur = ctx.db.execute(
            """INSERT INTO tasks (event_id, title, description, due_date, status, category, source,
                                  created_at, updated_at)
               VALUES (?, ?, ?, ?, 'todo', ?, 'ai', ?, ?)""",
            (event_id, t["title"], t["description"], add_days(event_date, -t["daysBeforeEvent"]),
             t["category"], ts, ts),
        )
        tid = int(cur.lastrowid)
        task_id_by_title[t["title"].lower()] = tid
        if t.get("dependsOn"):
            pending_deps.append((tid, t["dependsOn"]))
    for tid, dep_titles in pending_deps:
        for dep_title in dep_titles:
            prereq_id = task_id_by_title.get(dep_title.lower())
            if prereq_id is not None and prereq_id != tid:
                ctx.db.execute(
                    "INSERT OR IGNORE INTO task_dependencies (task_id, depends_on_id) VALUES (?, ?)",
                    (tid, prereq_id),
                )


def _insert_vendors(ctx: Context, event_id: int, new_vendors: list[dict]) -> None:
    for v in new_vendors:
        ctx.db.execute(
            "INSERT INTO vendors (event_id, name, category, status, quote_cents, contact) VALUES (?, ?, ?, 'researching', NULL, ?)",
            (event_id, v["name"], v["category"], v["contact"]),
        )


def apply_plan(ctx: Context, event: sqlite3.Row, plan_id: int, body: PlanApplyIn | None = None) -> dict:
    """Applies a draft with deterministic arithmetic: the model only supplied percentages and day offsets."""
    with transaction(ctx.db):
        row = _row(ctx, event["id"], plan_id)
        if row["status"] != "draft":
            raise conflict("This plan has already been applied or discarded", "not_a_draft")
        plan = json.loads(row["plan_json"])

        selected_cats, selected_tasks = _select(plan, body)
        existing_cats = {
            r["name"].lower() for r in ctx.db.execute("SELECT name FROM budget_categories WHERE event_id = ?", (event["id"],))
        }
        existing_task_rows = ctx.db.execute("SELECT id, title FROM tasks WHERE event_id = ?", (event["id"],)).fetchall()
        task_id_by_title = {r["title"].lower(): int(r["id"]) for r in existing_task_rows}
        existing_tasks = set(task_id_by_title)

        new_cats = [b for b in selected_cats if b["category"].lower() not in existing_cats]
        new_tasks = [t for t in selected_tasks if t["title"].lower() not in existing_tasks]

        include_vendors = bool(body and body.includeVendors)
        new_vendors, existing_vendor_count = _plan_vendors(ctx, event["id"], plan) if include_vendors else ([], 0)

        if (
            len(existing_cats) + len(new_cats) > BUDGET_LIMITS["categories"]
            or len(existing_tasks) + len(new_tasks) > TASK_LIMITS["tasks"]
            or existing_vendor_count + len(new_vendors) > MAX_VENDORS
        ):
            raise limit_reached("Applying this plan would exceed the per-event limits")

        ts = ctx.clock().isoformat()
        _insert_categories(ctx, event["id"], event["budget_cents"], new_cats)
        _insert_tasks(ctx, event["id"], event["event_date"], new_tasks, task_id_by_title, ts)
        _insert_vendors(ctx, event["id"], new_vendors)

        ctx.db.execute("UPDATE ai_plan_versions SET status = 'applied' WHERE id = ? AND event_id = ?", (plan_id, event["id"]))
        allocated = ctx.db.execute(
            "SELECT COALESCE(SUM(planned_cents), 0) AS a FROM budget_categories WHERE event_id = ?", (event["id"],)
        ).fetchone()["a"]
    result = {
        "categoriesCreated": len(new_cats),
        "categoriesSkipped": len(selected_cats) - len(new_cats),
        "tasksCreated": len(new_tasks),
        "tasksSkipped": len(selected_tasks) - len(new_tasks),
        "unallocatedCents": event["budget_cents"] - allocated,
    }
    if include_vendors:
        result["vendorsCreated"] = len(new_vendors)
    return result
