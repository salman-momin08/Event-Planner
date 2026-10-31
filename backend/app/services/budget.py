from __future__ import annotations

import sqlite3

from ..context import Context
from ..dates import to_date_string
from ..db import is_unique_violation, transaction, update_row
from ..errors import bad_request, conflict, limit_reached, not_found
from ..schemas import CategoryIn, CategoryPatch, ExpenseIn, ExpensePatch

LIMITS = {"categories": 100, "expenses": 1000}


def _category(r: sqlite3.Row) -> dict:
    return {"id": r["id"], "name": r["name"], "plannedCents": r["planned_cents"]}


def _expense(r: sqlite3.Row) -> dict:
    return {
        "id": r["id"],
        "categoryId": r["category_id"],
        "vendorId": r["vendor_id"],
        "description": r["description"],
        "amountCents": r["amount_cents"],
        "spentOn": r["spent_on"],
    }


def _check_limit(ctx: Context, table: str, event_id: int, maximum: int, label: str) -> None:
    n = ctx.db.execute(f"SELECT COUNT(*) AS n FROM {table} WHERE event_id = ?", (event_id,)).fetchone()["n"]
    if n >= maximum:
        raise limit_reached(f"An event can have at most {maximum} {label}")


def list_categories(ctx: Context, event_id: int) -> list[dict]:
    rows = ctx.db.execute("SELECT * FROM budget_categories WHERE event_id = ? ORDER BY name", (event_id,)).fetchall()
    return [_category(r) for r in rows]


def _get_category(ctx: Context, event_id: int, category_id: int) -> dict:
    row = ctx.db.execute(
        "SELECT * FROM budget_categories WHERE id = ? AND event_id = ?", (category_id, event_id)
    ).fetchone()
    if row is None:
        raise not_found("Category")
    return _category(row)


def _sync_category_spent(ctx: Context, event_id: int, category_id: int, target_spent_cents: int) -> None:
    current_spent = int(
        ctx.db.execute(
            "SELECT COALESCE(SUM(amount_cents), 0) AS s FROM expenses WHERE event_id = ? AND category_id = ?",
            (event_id, category_id),
        ).fetchone()["s"]
    )
    if target_spent_cents == current_spent:
        return
    if target_spent_cents == 0:
        ctx.db.execute("DELETE FROM expenses WHERE event_id = ? AND category_id = ?", (event_id, category_id))
        return
    if target_spent_cents > current_spent:
        diff = target_spent_cents - current_spent
        today = to_date_string(ctx.clock())
        adj = ctx.db.execute(
            "SELECT id, amount_cents FROM expenses WHERE event_id = ? AND category_id = ? AND description = 'Spent amount' ORDER BY id DESC LIMIT 1",
            (event_id, category_id),
        ).fetchone()
        if adj is not None:
            ctx.db.execute(
                "UPDATE expenses SET amount_cents = ? WHERE id = ? AND event_id = ?",
                (int(adj["amount_cents"]) + diff, adj["id"], event_id),
            )
        else:
            _check_limit(ctx, "expenses", event_id, LIMITS["expenses"], "expenses")
            ctx.db.execute(
                """INSERT INTO expenses (event_id, category_id, vendor_id, description, amount_cents, spent_on)
                   VALUES (?, ?, NULL, 'Spent amount', ?, ?)""",
                (event_id, category_id, diff, today),
            )
    else:
        # Replace category expenses with the exact updated spent amount
        today = to_date_string(ctx.clock())
        ctx.db.execute("DELETE FROM expenses WHERE event_id = ? AND category_id = ?", (event_id, category_id))
        ctx.db.execute(
            """INSERT INTO expenses (event_id, category_id, vendor_id, description, amount_cents, spent_on)
               VALUES (?, ?, NULL, 'Spent amount', ?, ?)""",
            (event_id, category_id, target_spent_cents, today),
        )


def create_category(ctx: Context, event_id: int, body: CategoryIn) -> dict:
    _check_limit(ctx, "budget_categories", event_id, LIMITS["categories"], "budget categories")
    try:
        with transaction(ctx.db):
            cur = ctx.db.execute(
                "INSERT INTO budget_categories (event_id, name, planned_cents) VALUES (?, ?, ?)",
                (event_id, body.name, body.plannedCents),
            )
            cat_id = int(cur.lastrowid)
            if body.spentCents is not None and body.spentCents > 0:
                _sync_category_spent(ctx, event_id, cat_id, body.spentCents)
    except sqlite3.IntegrityError as err:
        if is_unique_violation(err):
            raise conflict("A category with this name already exists") from None
        raise
    return _get_category(ctx, event_id, cat_id)


def update_category(ctx: Context, event_id: int, category_id: int, body: CategoryPatch) -> dict:
    _get_category(ctx, event_id, category_id)
    data = body.model_dump(exclude_unset=True)
    spent_cents = data.pop("spentCents", None)
    try:
        with transaction(ctx.db):
            if data:
                update_row(
                    ctx.db,
                    "budget_categories",
                    {"name": "name", "plannedCents": "planned_cents"},
                    data,
                    "id = ? AND event_id = ?",
                    (category_id, event_id),
                )
            if spent_cents is not None:
                _sync_category_spent(ctx, event_id, category_id, int(spent_cents))
    except sqlite3.IntegrityError as err:
        if is_unique_violation(err):
            raise conflict("A category with this name already exists") from None
        raise
    return _get_category(ctx, event_id, category_id)


def delete_category(ctx: Context, event_id: int, category_id: int) -> None:
    _get_category(ctx, event_id, category_id)
    n = ctx.db.execute(
        "SELECT COUNT(*) AS n FROM expenses WHERE category_id = ? AND event_id = ?", (category_id, event_id)
    ).fetchone()["n"]
    if n:
        raise conflict("Move or delete this category’s expenses first", "category_in_use")
    ctx.db.execute("DELETE FROM budget_categories WHERE id = ? AND event_id = ?", (category_id, event_id))


def _assert_refs(ctx: Context, event_id: int, category_id: int | None, vendor_id: int | None) -> None:
    errors: dict[str, str] = {}
    if category_id is not None and not ctx.db.execute(
        "SELECT 1 FROM budget_categories WHERE id = ? AND event_id = ?", (category_id, event_id)
    ).fetchone():
        errors["categoryId"] = "Category not found in this event"
    if vendor_id is not None and not ctx.db.execute(
        "SELECT 1 FROM vendors WHERE id = ? AND event_id = ?", (vendor_id, event_id)
    ).fetchone():
        errors["vendorId"] = "Vendor not found in this event"
    if errors:
        raise bad_request(errors)


def list_expenses(ctx: Context, event_id: int) -> list[dict]:
    rows = ctx.db.execute(
        "SELECT * FROM expenses WHERE event_id = ? ORDER BY spent_on DESC, id DESC", (event_id,)
    ).fetchall()
    return [_expense(r) for r in rows]


def _get_expense(ctx: Context, event_id: int, expense_id: int) -> dict:
    row = ctx.db.execute("SELECT * FROM expenses WHERE id = ? AND event_id = ?", (expense_id, event_id)).fetchone()
    if row is None:
        raise not_found("Expense")
    return _expense(row)


def create_expense(ctx: Context, event_id: int, body: ExpenseIn) -> dict:
    _assert_refs(ctx, event_id, body.categoryId, body.vendorId)
    _check_limit(ctx, "expenses", event_id, LIMITS["expenses"], "expenses")
    cur = ctx.db.execute(
        """INSERT INTO expenses (event_id, category_id, vendor_id, description, amount_cents, spent_on)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (event_id, body.categoryId, body.vendorId, body.description, body.amountCents, body.spentOn),
    )
    return _get_expense(ctx, event_id, int(cur.lastrowid))


def update_expense(ctx: Context, event_id: int, expense_id: int, body: ExpensePatch) -> dict:
    _get_expense(ctx, event_id, expense_id)
    data = body.model_dump(exclude_unset=True)
    _assert_refs(ctx, event_id, data.get("categoryId"), data.get("vendorId"))
    update_row(
        ctx.db, "expenses",
        {"categoryId": "category_id", "vendorId": "vendor_id", "description": "description",
         "amountCents": "amount_cents", "spentOn": "spent_on"},
        data, "id = ? AND event_id = ?", (expense_id, event_id),
    )
    return _get_expense(ctx, event_id, expense_id)


def delete_expense(ctx: Context, event_id: int, expense_id: int) -> None:
    _get_expense(ctx, event_id, expense_id)
    ctx.db.execute("DELETE FROM expenses WHERE id = ? AND event_id = ?", (expense_id, event_id))


def summarize(ctx: Context, event: sqlite3.Row) -> dict:
    """Deterministic budget summary (FR-007). All arithmetic is integer minor units."""
    rows = ctx.db.execute(
        """SELECT c.id, c.name, c.planned_cents, COALESCE(SUM(e.amount_cents), 0) AS spent
           FROM budget_categories c LEFT JOIN expenses e ON e.category_id = c.id
           WHERE c.event_id = ? GROUP BY c.id ORDER BY c.name""",
        (event["id"],),
    ).fetchall()
    categories = []
    for r in rows:
        if r["spent"] > r["planned_cents"]:
            status = "over"
        elif r["planned_cents"] > 0 and r["spent"] * 100 >= r["planned_cents"] * 90:
            status = "near_limit"
        else:
            status = "on_track"
        categories.append(
            {
                "id": r["id"],
                "name": r["name"],
                "plannedCents": r["planned_cents"],
                "spentCents": r["spent"],
                "varianceCents": r["planned_cents"] - r["spent"],
                "status": status,
            }
        )
    allocated = sum(c["plannedCents"] for c in categories)
    spent = sum(c["spentCents"] for c in categories)
    total = event["budget_cents"]
    return {
        "totalCents": total,
        "allocatedCents": allocated,
        "unallocatedCents": total - allocated,
        "overAllocated": allocated > total,
        "spentCents": spent,
        "remainingCents": total - spent,
        "overBudget": spent > total,
        "currency": event["currency"],
        "categories": categories,
    }
