from __future__ import annotations

import sqlite3

from ..context import Context
from ..dates import add_days, to_date_string
from ..db import transaction
from ..errors import limit_reached
from .tasks import LIMITS, list_tasks

# (title, category, days before the event, prerequisite title or None)
WEDDING = [
    ("Set budget and guest-count estimate", "Planning", 35, None),
    ("Book venue", "Venue", 32, "Set budget and guest-count estimate"),
    ("Book photographer/videographer", "Photography", 30, "Book venue"),
    ("Book caterer", "Catering", 27, "Book venue"),
    ("Book officiant and music/DJ", "Entertainment", 24, "Book venue"),
    ("Choose attire", "Attire", 21, None),
    ("Send save-the-dates", "Guests", 18, "Book venue"),
    ("Book decor and florist", "Decor", 15, "Book venue"),
    ("Send invitations", "Guests", 12, "Send save-the-dates"),
    ("Finalise menu and cake", "Catering", 9, "Book caterer"),
    ("Confirm seating plan", "Guests", 6, "Send invitations"),
    ("Confirm all vendors and timeline", "Vendors", 4, "Confirm seating plan"),
    ("Final payments", "Budget", 2, "Confirm all vendors and timeline"),
    ("Rehearsal", "Ceremony", 1, "Confirm all vendors and timeline"),
]
BIRTHDAY = [
    ("Set budget and guest list", "Planning", 30, None),
    ("Choose date and venue", "Venue", 27, "Set budget and guest list"),
    ("Pick theme", "Theme", 24, "Set budget and guest list"),
    ("Send invitations", "Guests", 21, "Choose date and venue"),
    ("Order cake", "Catering", 14, "Pick theme"),
    ("Plan food and drinks", "Catering", 10, "Choose date and venue"),
    ("Buy decorations and party favours", "Decor", 7, "Pick theme"),
    ("Plan activities and music", "Entertainment", 5, None),
    ("Confirm headcount", "Guests", 3, "Send invitations"),
    ("Set up venue", "Venue", 0, "Confirm headcount"),
]
COMMUNITY = [
    ("Define goals, budget and volunteer needs", "Planning", 30, None),
    ("Secure permits and insurance", "Compliance", 27, "Define goals, budget and volunteer needs"),
    ("Book venue or site", "Venue", 24, "Secure permits and insurance"),
    ("Recruit volunteers", "Volunteers", 21, "Define goals, budget and volunteer needs"),
    ("Book vendors and equipment", "Vendors", 18, "Book venue or site"),
    ("Launch promotion", "Marketing", 15, "Book venue or site"),
    ("Confirm sponsors and donations", "Budget", 12, "Define goals, budget and volunteer needs"),
    ("Create run-of-show and volunteer schedule", "Logistics", 7, "Recruit volunteers"),
    ("Safety and accessibility walkthrough", "Compliance", 3, "Create run-of-show and volunteer schedule"),
    ("Final briefing with volunteers", "Volunteers", 1, "Safety and accessibility walkthrough"),
    ("Post-event thanks and debrief", "Follow-up", 0, "Final briefing with volunteers"),
]
TEMPLATES = {"wedding": WEDDING, "birthday": BIRTHDAY, "community": COMMUNITY}


def generate_timeline(ctx: Context, event: sqlite3.Row) -> dict:
    today = to_date_string(ctx.clock())
    with transaction(ctx.db):
        # Also repair any existing template tasks on this event that had legacy 300/270-day offsets
        template_days = {title.lower(): days for title, _, days, _ in TEMPLATES[event["type"]]}
        existing_rows = ctx.db.execute("SELECT id, title, source FROM tasks WHERE event_id = ?", (event["id"],)).fetchall()
        id_by_title = {r["title"].lower(): int(r["id"]) for r in existing_rows}
        ts = ctx.clock().isoformat()
        for r in existing_rows:
            key = r["title"].lower()
            if r["source"] == "template" and key in template_days:
                due = max(today, add_days(event["event_date"], -template_days[key])) if event["event_date"] >= today else add_days(event["event_date"], -template_days[key])
                ctx.db.execute(
                    "UPDATE tasks SET due_date = ?, updated_at = ? WHERE id = ? AND event_id = ?",
                    (due, ts, r["id"], event["id"]),
                )
        count = len(id_by_title)
        created = skipped = 0
        created_Prereqs: list[tuple[int, str]] = []
        for title, category, days, prereq in TEMPLATES[event["type"]]:
            if title.lower() in id_by_title:
                skipped += 1
                continue
            if count >= LIMITS["tasks"]:
                raise limit_reached(f"An event can have at most {LIMITS['tasks']} tasks")
            raw_due = add_days(event["event_date"], -days)
            due_date = max(today, raw_due) if event["event_date"] >= today else raw_due
            cur = ctx.db.execute(
                """INSERT INTO tasks (event_id, title, description, due_date, status, category, source,
                                      created_at, updated_at)
                   VALUES (?, ?, '', ?, 'todo', ?, 'template', ?, ?)""",
                (event["id"], title, due_date, category, ts, ts),
            )
            task_id = int(cur.lastrowid)
            id_by_title[title.lower()] = task_id
            if prereq:
                created_Prereqs.append((task_id, prereq.lower()))
            count += 1
            created += 1
        for task_id, prereq_key in created_Prereqs:
            prereq_id = id_by_title.get(prereq_key)
            if prereq_id is not None and prereq_id != task_id:
                ctx.db.execute(
                    "INSERT OR IGNORE INTO task_dependencies (task_id, depends_on_id) VALUES (?, ?)",
                    (task_id, prereq_id),
                )
    return {"created": created, "skipped": skipped}
