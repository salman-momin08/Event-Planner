from __future__ import annotations

import sqlite3

from ..context import Context
from ..db import is_unique_violation, transaction, update_row
from ..dates import to_date_string
from ..errors import bad_request, conflict, limit_reached, not_found
from ..schemas import TaskIn, TaskPatch

LIMITS = {"tasks": 500}
COLUMNS = {
    "title": "title",
    "description": "description",
    "dueDate": "due_date",
    "status": "status",
    "category": "category",
    "vendorId": "vendor_id",
}


def _dependency_map(ctx: Context, event_id: int) -> dict[int, list[int]]:
    rows = ctx.db.execute(
        """SELECT td.task_id, td.depends_on_id FROM task_dependencies td
           JOIN tasks t ON t.id = td.task_id WHERE t.event_id = ?""",
        (event_id,),
    ).fetchall()
    graph: dict[int, list[int]] = {}
    for r in rows:
        graph.setdefault(r["task_id"], []).append(r["depends_on_id"])
    return graph


def _decorate(rows: list[sqlite3.Row], graph: dict[int, list[int]], today: str) -> list[dict]:
    status_by_id = {r["id"]: r["status"] for r in rows}
    tasks = []
    for r in rows:
        depends_on = graph.get(r["id"], [])
        open_ = r["status"] != "done"
        tasks.append(
            {
                "id": r["id"],
                "title": r["title"],
                "description": r["description"],
                "dueDate": r["due_date"],
                "status": r["status"],
                "category": r["category"],
                "vendorId": r["vendor_id"],
                "source": r["source"],
                "dependsOn": depends_on,
                "blocked": open_ and any(status_by_id.get(d) != "done" for d in depends_on),
                "overdue": open_ and r["due_date"] is not None and r["due_date"] < today,
            }
        )
    return tasks


def list_tasks(ctx: Context, event_id: int) -> list[dict]:
    rows = ctx.db.execute(
        "SELECT * FROM tasks WHERE event_id = ? ORDER BY due_date IS NULL, due_date, id", (event_id,)
    ).fetchall()
    return _decorate(rows, _dependency_map(ctx, event_id), to_date_string(ctx.clock()))


def _get_task(ctx: Context, event_id: int, task_id: int) -> dict:
    row = ctx.db.execute("SELECT * FROM tasks WHERE id = ? AND event_id = ?", (task_id, event_id)).fetchone()
    if row is None:
        raise not_found("Task")
    dep_rows = ctx.db.execute(
        """SELECT td.depends_on_id, p.status FROM task_dependencies td
           JOIN tasks p ON p.id = td.depends_on_id WHERE td.task_id = ?""",
        (task_id,),
    ).fetchall()
    depends_on = [d["depends_on_id"] for d in dep_rows]
    today = to_date_string(ctx.clock())
    open_ = row["status"] != "done"
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "dueDate": row["due_date"],
        "status": row["status"],
        "category": row["category"],
        "vendorId": row["vendor_id"],
        "source": row["source"],
        "dependsOn": depends_on,
        "blocked": open_ and any(d["status"] != "done" for d in dep_rows),
        "overdue": open_ and row["due_date"] is not None and row["due_date"] < today,
    }


def _assert_vendor(ctx: Context, event_id: int, vendor_id: int | None) -> None:
    if vendor_id is not None and not ctx.db.execute(
        "SELECT 1 FROM vendors WHERE id = ? AND event_id = ?", (vendor_id, event_id)
    ).fetchone():
        raise bad_request({"vendorId": "Vendor not found in this event"})


def _set_dependencies(ctx: Context, event_id: int, task_id: int, ids: list[int]) -> None:
    if ids:
        marks = ",".join("?" * len(ids))
        found = ctx.db.execute(f"SELECT id FROM tasks WHERE event_id = ? AND id IN ({marks})", (event_id, *ids)).fetchall()
        if len(found) != len(ids):
            raise bad_request({"dependsOn": "All prerequisites must be tasks in this event"})
    if task_id in ids:
        raise bad_request({"dependsOn": "A task cannot depend on itself"})

    graph = _dependency_map(ctx, event_id)
    graph[task_id] = list(ids)
    seen: set[int] = set()
    stack = list(ids)
    while stack:
        current = stack.pop()
        if current == task_id:
            raise bad_request({"dependsOn": "Dependencies must not form a cycle"})
        if current in seen:
            continue
        seen.add(current)
        stack.extend(graph.get(current, []))
    ctx.db.execute("DELETE FROM task_dependencies WHERE task_id = ?", (task_id,))
    ctx.db.executemany("INSERT INTO task_dependencies (task_id, depends_on_id) VALUES (?, ?)", [(task_id, i) for i in ids])


def create_task(ctx: Context, event_id: int, body: TaskIn, source: str = "manual") -> dict:
    _assert_vendor(ctx, event_id, body.vendorId)
    n = ctx.db.execute("SELECT COUNT(*) AS n FROM tasks WHERE event_id = ?", (event_id,)).fetchone()["n"]
    if n >= LIMITS["tasks"]:
        raise limit_reached(f"An event can have at most {LIMITS['tasks']} tasks")
    with transaction(ctx.db):
        ts = ctx.clock().isoformat()
        try:
            cur = ctx.db.execute(
                """INSERT INTO tasks (event_id, title, description, due_date, status, category, vendor_id,
                                      source, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (event_id, body.title, body.description, body.dueDate, body.status, body.category,
                 body.vendorId, source, ts, ts),
            )
        except sqlite3.IntegrityError as err:
            if is_unique_violation(err):
                raise conflict("A task with this title already exists") from None
            raise
        task_id = int(cur.lastrowid)
        if body.dependsOn:
            _set_dependencies(ctx, event_id, task_id, body.dependsOn)
    return _get_task(ctx, event_id, task_id)


def update_task(ctx: Context, event_id: int, task_id: int, body: TaskPatch) -> dict:
    _get_task(ctx, event_id, task_id)
    data = body.model_dump(exclude_unset=True)
    _assert_vendor(ctx, event_id, data.get("vendorId"))
    with transaction(ctx.db):
        try:
            update_row(ctx.db, "tasks", COLUMNS, data, "id = ? AND event_id = ?", (task_id, event_id))
        except sqlite3.IntegrityError as err:
            if is_unique_violation(err):
                raise conflict("A task with this title already exists") from None
            raise
        ctx.db.execute(
            "UPDATE tasks SET updated_at = ? WHERE id = ? AND event_id = ?", (ctx.clock().isoformat(), task_id, event_id)
        )
        if "dependsOn" in data:
            _set_dependencies(ctx, event_id, task_id, data["dependsOn"])
    return _get_task(ctx, event_id, task_id)


def delete_task(ctx: Context, event_id: int, task_id: int) -> None:
    _get_task(ctx, event_id, task_id)
    ctx.db.execute("DELETE FROM tasks WHERE id = ? AND event_id = ?", (task_id, event_id))


def timeline(ctx: Context, event_id: int) -> dict:
    tasks = list_tasks(ctx, event_id)
    return {
        "today": to_date_string(ctx.clock()),
        "dated": [t for t in tasks if t["dueDate"] is not None],
        "undated": [t for t in tasks if t["dueDate"] is None],
    }


def task_stats(ctx: Context, event_id: int) -> dict:
    today = to_date_string(ctx.clock())
    row = ctx.db.execute(
        """SELECT
             COUNT(*) AS total,
             COALESCE(SUM(t.status = 'done'), 0) AS done,
             COALESCE(SUM(t.status != 'done' AND t.due_date IS NOT NULL AND t.due_date < ?), 0) AS overdue,
             COALESCE(SUM(
               t.status != 'done' AND EXISTS (
                 SELECT 1 FROM task_dependencies td
                 JOIN tasks p ON p.id = td.depends_on_id
                 WHERE td.task_id = t.id AND p.status != 'done'
               )
             ), 0) AS blocked
           FROM tasks t WHERE t.event_id = ?""",
        (today, event_id),
    ).fetchone()
    return {
        "total": row["total"],
        "done": row["done"],
        "overdue": row["overdue"],
        "blocked": row["blocked"],
    }
