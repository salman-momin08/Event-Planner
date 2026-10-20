from __future__ import annotations

import sqlite3

from ..context import Context
from ..db import update_row
from ..errors import not_found
from ..schemas import EventIn, EventPatch

COLUMNS = {
    "type": "type",
    "title": "title",
    "eventDate": "event_date",
    "attendance": "attendance",
    "location": "location",
    "budgetCents": "budget_cents",
    "currency": "currency",
    "notes": "notes",
}
MAX_ID = 2**62


def to_event(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "type": row["type"],
        "title": row["title"],
        "eventDate": row["event_date"],
        "attendance": row["attendance"],
        "location": row["location"],
        "budgetCents": row["budget_cents"],
        "currency": row["currency"],
        "notes": row["notes"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


def require_event(ctx: Context, user_id: int, event_id: int) -> sqlite3.Row:
    """The single ownership choke-point (SEC-004): foreign and missing events look identical."""
    row = None
    if 0 < event_id < MAX_ID:
        row = ctx.db.execute("SELECT * FROM events WHERE id = ? AND owner_id = ?", (event_id, user_id)).fetchone()
    if row is None:
        raise not_found("Event")
    return row


def create_event(ctx: Context, user_id: int, body: EventIn) -> dict:
    ts = ctx.clock().isoformat()
    cur = ctx.db.execute(
        """INSERT INTO events (owner_id, type, title, event_date, attendance, location, budget_cents,
                               currency, notes, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, body.type, body.title, body.eventDate, body.attendance, body.location,
         body.budgetCents, body.currency, body.notes, ts, ts),
    )
    return to_event(require_event(ctx, user_id, int(cur.lastrowid)))


def list_events(ctx: Context, user_id: int, limit: int, offset: int) -> list[dict]:
    rows = ctx.db.execute(
        "SELECT * FROM events WHERE owner_id = ? ORDER BY event_date ASC, id ASC LIMIT ? OFFSET ?",
        (user_id, limit, offset),
    ).fetchall()
    return [to_event(r) for r in rows]


def update_event(ctx: Context, user_id: int, event_id: int, body: EventPatch) -> dict:
    require_event(ctx, user_id, event_id)
    update_row(ctx.db, "events", COLUMNS, body.model_dump(exclude_unset=True), "id = ? AND owner_id = ?", (event_id, user_id))
    ctx.db.execute(
        "UPDATE events SET updated_at = ? WHERE id = ? AND owner_id = ?",
        (ctx.clock().isoformat(), event_id, user_id),
    )
    return to_event(require_event(ctx, user_id, event_id))


def delete_event(ctx: Context, user_id: int, event_id: int) -> None:
    require_event(ctx, user_id, event_id)
    ctx.db.execute("DELETE FROM events WHERE id = ? AND owner_id = ?", (event_id, user_id))
