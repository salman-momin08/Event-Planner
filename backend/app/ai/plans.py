from __future__ import annotations

import json
import sqlite3
import time

from ..context import Context
from ..dates import add_days, to_date_string
from ..db import transaction
from ..errors import ApiError, bad_request, conflict, limit_reached, not_found
from ..money import percent_to_cents
from ..schemas import PlanRequest
from ..security import enforce
from ..services.budget import LIMITS as BUDGET_LIMITS
from ..services.tasks import LIMITS as TASK_LIMITS
from .graph import run_plan_graph
from .prompts import PROMPT_VERSION, build_context, context_json

MAX_PLANS_PER_EVENT = 50


def _plan(r: sqlite3.Row) -> dict:
    return {
        "id": r["id"],
        "eventId": r["event_id"],
        "parentId": r["parent_id"],
        "status": r["status"],
        "instruction": r["instruction"],
        "preferences": r["preferences"],
        "plan": json.loads(r["plan_json"]),
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

    previous_plan = json.loads(_row(ctx, event["id"], body.parentId)["plan_json"]) if body.parentId else None
    n = ctx.db.execute("SELECT COUNT(*) AS n FROM ai_plan_versions WHERE event_id = ?", (event["id"],)).fetchone()["n"]
    if n >= MAX_PLANS_PER_EVENT:
        raise limit_reached(f"An event can keep at most {MAX_PLANS_PER_EVENT} AI drafts; discard some first")

    enforce(ctx.limiters["ai_minute"], f"ai:{user['id']}", "AI requests are limited to a few per minute")
    enforce(ctx.limiters["ai_daily"], f"ai:{user['id']}", "Daily AI request limit reached")

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


def apply_plan(ctx: Context, event: sqlite3.Row, plan_id: int) -> dict:
    """Applies a draft with deterministic arithmetic: the model only supplied percentages and day offsets."""
    with transaction(ctx.db):
        row = _row(ctx, event["id"], plan_id)
        if row["status"] != "draft":
            raise conflict("This plan has already been applied or discarded", "not_a_draft")
        plan = json.loads(row["plan_json"])

        existing_cats = {
            r["name"].lower() for r in ctx.db.execute("SELECT name FROM budget_categories WHERE event_id = ?", (event["id"],))
        }
        existing_tasks = {
            r["title"].lower() for r in ctx.db.execute("SELECT title FROM tasks WHERE event_id = ?", (event["id"],))
        }
        new_cats = [b for b in plan["budgetAllocations"] if b["category"].lower() not in existing_cats]
        new_tasks = [t for t in plan["tasks"] if t["title"].lower() not in existing_tasks]
        if (
            len(existing_cats) + len(new_cats) > BUDGET_LIMITS["categories"]
            or len(existing_tasks) + len(new_tasks) > TASK_LIMITS["tasks"]
        ):
            raise limit_reached("Applying this plan would exceed the per-event limits")

        for b in new_cats:
            ctx.db.execute(
                "INSERT INTO budget_categories (event_id, name, planned_cents) VALUES (?, ?, ?)",
                (event["id"], b["category"], percent_to_cents(event["budget_cents"], b["percent"])),
            )
        ts = ctx.clock().isoformat()
        for t in new_tasks:
            ctx.db.execute(
                """INSERT INTO tasks (event_id, title, description, due_date, status, category, source,
                                      created_at, updated_at)
                   VALUES (?, ?, ?, ?, 'todo', ?, 'ai', ?, ?)""",
                (event["id"], t["title"], t["description"], add_days(event["event_date"], -t["daysBeforeEvent"]),
                 t["category"], ts, ts),
            )
        ctx.db.execute("UPDATE ai_plan_versions SET status = 'applied' WHERE id = ? AND event_id = ?", (plan_id, event["id"]))
        allocated = ctx.db.execute(
            "SELECT COALESCE(SUM(planned_cents), 0) AS a FROM budget_categories WHERE event_id = ?", (event["id"],)
        ).fetchone()["a"]
    return {
        "categoriesCreated": len(new_cats),
        "categoriesSkipped": len(plan["budgetAllocations"]) - len(new_cats),
        "tasksCreated": len(new_tasks),
        "tasksSkipped": len(plan["tasks"]) - len(new_tasks),
        "unallocatedCents": event["budget_cents"] - allocated,
    }
