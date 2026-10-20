from __future__ import annotations

import re
import sqlite3

from ..context import Context
from ..money import cents_to_decimal
from .budget import list_categories, list_expenses
from .events import to_event
from .tasks import list_tasks
from .vendors import list_vendors

CSV_SECTIONS = ("tasks", "expenses", "vendors")
# Cells beginning with these characters can be executed as formulas by spreadsheet apps (SEC-015).
_FORMULA_START = re.compile(r"^[=+\-@\t\r\n]")


class Raw(str):
    """A trusted, already-formatted value (e.g. an amount) that must not be neutralised."""


def export_json(ctx: Context, event: sqlite3.Row) -> dict:
    return {
        "exportedAt": ctx.clock().isoformat(),
        "event": to_event(event),
        "budgetCategories": list_categories(ctx, event["id"]),
        "expenses": list_expenses(ctx, event["id"]),
        "tasks": list_tasks(ctx, event["id"]),
        "vendors": list_vendors(ctx, event["id"]),
    }


def csv_cell(value: object) -> str:
    if isinstance(value, Raw):
        text = str(value)
    else:
        text = "" if value is None else str(value)
        if _FORMULA_START.match(text):
            text = "'" + text
    return '"' + text.replace('"', '""') + '"'


def _to_csv(header: list[str], rows: list[list[object]]) -> str:
    return "\r\n".join(",".join(csv_cell(c) for c in row) for row in [header, *rows]) + "\r\n"


def _amount(cents: int | None) -> Raw:
    return Raw("" if cents is None else cents_to_decimal(cents))


def export_csv(ctx: Context, event: sqlite3.Row, section: str) -> str:
    event_id = event["id"]
    if section == "tasks":
        return _to_csv(
            ["Title", "Description", "Due date", "Status", "Category", "Blocked", "Overdue"],
            [
                [t["title"], t["description"], t["dueDate"], t["status"], t["category"],
                 "yes" if t["blocked"] else "no", "yes" if t["overdue"] else "no"]
                for t in list_tasks(ctx, event_id)
            ],
        )
    if section == "expenses":
        names = {c["id"]: c["name"] for c in list_categories(ctx, event_id)}
        return _to_csv(
            ["Date", "Description", "Category", f"Amount ({event['currency']})"],
            [[x["spentOn"], x["description"], names.get(x["categoryId"]), _amount(x["amountCents"])] for x in list_expenses(ctx, event_id)],
        )
    return _to_csv(
        ["Name", "Category", "Status", f"Quote ({event['currency']})", "Contact notes"],
        [[v["name"], v["category"], v["status"], _amount(v["quoteCents"]), v["contact"]] for v in list_vendors(ctx, event_id)],
    )
