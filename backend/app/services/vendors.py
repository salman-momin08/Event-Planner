from __future__ import annotations

import sqlite3

from ..context import Context
from ..db import update_row
from ..errors import limit_reached, not_found
from ..schemas import VendorIn, VendorPatch

MAX_VENDORS = 200


def _vendor(r: sqlite3.Row) -> dict:
    return {
        "id": r["id"],
        "name": r["name"],
        "category": r["category"],
        "status": r["status"],
        "quoteCents": r["quote_cents"],
        "contact": r["contact"],
    }


def list_vendors(ctx: Context, event_id: int) -> list[dict]:
    rows = ctx.db.execute(
        "SELECT * FROM vendors WHERE event_id = ? ORDER BY name COLLATE NOCASE, id", (event_id,)
    ).fetchall()
    return [_vendor(r) for r in rows]


def _get(ctx: Context, event_id: int, vendor_id: int) -> dict:
    row = ctx.db.execute("SELECT * FROM vendors WHERE id = ? AND event_id = ?", (vendor_id, event_id)).fetchone()
    if row is None:
        raise not_found("Vendor")
    return _vendor(row)


def create_vendor(ctx: Context, event_id: int, body: VendorIn) -> dict:
    n = ctx.db.execute("SELECT COUNT(*) AS n FROM vendors WHERE event_id = ?", (event_id,)).fetchone()["n"]
    if n >= MAX_VENDORS:
        raise limit_reached(f"An event can have at most {MAX_VENDORS} vendors")
    cur = ctx.db.execute(
        "INSERT INTO vendors (event_id, name, category, status, quote_cents, contact) VALUES (?, ?, ?, ?, ?, ?)",
        (event_id, body.name, body.category, body.status, body.quoteCents, body.contact),
    )
    return _get(ctx, event_id, int(cur.lastrowid))


def update_vendor(ctx: Context, event_id: int, vendor_id: int, body: VendorPatch) -> dict:
    _get(ctx, event_id, vendor_id)
    update_row(
        ctx.db, "vendors",
        {"name": "name", "category": "category", "status": "status", "quoteCents": "quote_cents", "contact": "contact"},
        body.model_dump(exclude_unset=True), "id = ? AND event_id = ?", (vendor_id, event_id),
    )
    return _get(ctx, event_id, vendor_id)


def delete_vendor(ctx: Context, event_id: int, vendor_id: int) -> None:
    _get(ctx, event_id, vendor_id)
    ctx.db.execute("DELETE FROM vendors WHERE id = ? AND event_id = ?", (vendor_id, event_id))
