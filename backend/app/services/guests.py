from __future__ import annotations

import sqlite3

from ..context import Context
from ..db import update_row
from ..errors import limit_reached, not_found
from ..schemas import GuestIn, GuestPatch

MAX_GUESTS = 500

COLUMNS = {
    "name": "name",
    "contact": "contact",
    "rsvpStatus": "rsvp_status",
    "partySize": "party_size",
    "dietary": "dietary",
    "tableGroup": "table_group",
    "notes": "notes",
}


def _guest(r: sqlite3.Row) -> dict:
    return {
        "id": r["id"],
        "name": r["name"],
        "contact": r["contact"],
        "rsvpStatus": r["rsvp_status"],
        "partySize": r["party_size"],
        "dietary": r["dietary"],
        "tableGroup": r["table_group"],
        "notes": r["notes"],
        "createdAt": r["created_at"],
    }


def list_guests(ctx: Context, event_id: int) -> list[dict]:
    rows = ctx.db.execute(
        "SELECT * FROM guests WHERE event_id = ? ORDER BY name COLLATE NOCASE, id",
        (event_id,),
    ).fetchall()
    return [_guest(r) for r in rows]


def _get(ctx: Context, event_id: int, guest_id: int) -> dict:
    row = ctx.db.execute("SELECT * FROM guests WHERE id = ? AND event_id = ?", (guest_id, event_id)).fetchone()
    if row is None:
        raise not_found("Guest")
    return _guest(row)


def create_guest(ctx: Context, event_id: int, body: GuestIn) -> dict:
    n = ctx.db.execute("SELECT COUNT(*) AS n FROM guests WHERE event_id = ?", (event_id,)).fetchone()["n"]
    if n >= MAX_GUESTS:
        raise limit_reached(f"An event can have at most {MAX_GUESTS} guest entries")
    ts = ctx.clock().isoformat()
    cur = ctx.db.execute(
        """INSERT INTO guests (event_id, name, contact, rsvp_status, party_size, dietary, table_group, notes, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (event_id, body.name, body.contact, body.rsvpStatus, body.partySize, body.dietary, body.tableGroup, body.notes, ts),
    )
    return _get(ctx, event_id, int(cur.lastrowid))


def update_guest(ctx: Context, event_id: int, guest_id: int, body: GuestPatch) -> dict:
    _get(ctx, event_id, guest_id)
    update_row(
        ctx.db,
        "guests",
        COLUMNS,
        body.model_dump(exclude_unset=True),
        "id = ? AND event_id = ?",
        (guest_id, event_id),
    )
    return _get(ctx, event_id, guest_id)


def delete_guest(ctx: Context, event_id: int, guest_id: int) -> None:
    _get(ctx, event_id, guest_id)
    ctx.db.execute("DELETE FROM guests WHERE id = ? AND event_id = ?", (guest_id, event_id))


def guest_stats(ctx: Context, event_id: int) -> dict:
    rows = ctx.db.execute(
        "SELECT rsvp_status, party_size, dietary FROM guests WHERE event_id = ?",
        (event_id,),
    ).fetchall()
    attending = sum(r["party_size"] for r in rows if r["rsvp_status"] == "attending")
    pending = sum(r["party_size"] for r in rows if r["rsvp_status"] == "pending")
    maybe = sum(r["party_size"] for r in rows if r["rsvp_status"] == "maybe")
    declined = sum(r["party_size"] for r in rows if r["rsvp_status"] == "declined")
    dietary_counts: dict[str, int] = {}
    for r in rows:
        if r["rsvp_status"] in {"attending", "maybe", "pending"} and r["dietary"] != "none":
            dietary_counts[r["dietary"]] = dietary_counts.get(r["dietary"], 0) + int(r["party_size"])
    return {
        "entries": len(rows),
        "attendingHeadcount": attending,
        "pendingHeadcount": pending,
        "maybeHeadcount": maybe,
        "declinedHeadcount": declined,
        "dietaryBreakdown": dietary_counts,
    }
