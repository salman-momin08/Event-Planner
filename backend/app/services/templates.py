from __future__ import annotations

import sqlite3

from ..context import Context
from ..dates import add_days
from ..db import transaction
from ..errors import limit_reached
from .tasks import LIMITS, list_tasks

# (title, category, days before the event, prerequisite title or None)
WEDDING = [
    ("Set budget and guest-count estimate", "Planning", 365, None),
    ("Book venue", "Venue", 330, "Set budget and guest-count estimate"),
    ("Book photographer/videographer", "Photography", 300, "Book venue"),
    ("Book caterer", "Catering", 270, "Book venue"),
    ("Book officiant and music/DJ", "Entertainment", 240, "Book venue"),
    ("Choose attire", "Attire", 210, None),
    ("Send save-the-dates", "Guests", 180, "Book venue"),
    ("Book decor and florist", "Decor", 150, "Book venue"),
    ("Send invitations", "Guests", 90, "Send save-the-dates"),
    ("Finalise menu and cake", "Catering", 60, "Book caterer"),
    ("Confirm RSVPs and seating plan", "Guests", 21, "Send invitations"),
    ("Confirm all vendors and timeline", "Vendors", 14, "Confirm RSVPs and seating plan"),
    ("Final payments", "Budget", 7, "Confirm all vendors and timeline"),
    ("Rehearsal", "Ceremony", 1, "Confirm all vendors and timeline"),
]
BIRTHDAY = [
    ("Set budget and guest list", "Planning", 42, None),
    ("Choose date and venue", "Venue", 35, "Set budget and guest list"),
    ("Pick theme", "Theme", 28, "Set budget and guest list"),
    ("Send invitations", "Guests", 21, "Choose date and venue"),
    ("Order cake", "Catering", 14, "Pick theme"),
    ("Plan food and drinks", "Catering", 10, "Choose date and venue"),
    ("Buy decorations and party favours", "Decor", 7, "Pick theme"),
    ("Plan activities and music", "Entertainment", 5, None),
    ("Confirm RSVPs", "Guests", 3, "Send invitations"),
    ("Set up venue", "Venue", 0, "Confirm RSVPs"),
]
COMMUNITY = [
    ("Define goals, budget and volunteer needs", "Planning", 120, None),
    ("Secure permits and insurance", "Compliance", 100, "Define goals, budget and volunteer needs"),
    ("Book venue or site", "Venue", 90, "Secure permits and insurance"),
    ("Recruit volunteers", "Volunteers", 75, "Define goals, budget and volunteer needs"),
    ("Book vendors and equipment", "Vendors", 60, "Book venue or site"),
    ("Launch promotion", "Marketing", 45, "Book venue or site"),
    ("Confirm sponsors and donations", "Budget", 30, "Define goals, budget and volunteer needs"),
    ("Create run-of-show and volunteer schedule", "Logistics", 14, "Recruit volunteers"),
    ("Safety and accessibility walkthrough", "Compliance", 7, "Create run-of-show and volunteer schedule"),
    ("Final briefing with volunteers", "Volunteers", 1, "Safety and accessibility walkthrough"),
    ("Post-event thanks and debrief", "Follow-up", -3, "Final briefing with volunteers"),
]
TEMPLATES = {"wedding": WEDDING, "birthday": BIRTHDAY, "community": COMMUNITY}


def generate_timeline(ctx: Context, event: sqlite3.Row) -> dict:
    with transaction(ctx.db):
        existing_rows = ctx.db.execute("SELECT id, title FROM tasks WHERE event_id = ?", (event["id"],)).fetchall()
        id_by_title = {r["title"].lower(): int(r["id"]) for r in existing_rows}
        count = len(id_by_title)
        created = skipped = 0
        created_Prereqs: list[tuple[int, str]] = []
        ts = ctx.clock().isoformat()
        for title, category, days, prereq in TEMPLATES[event["type"]]:
            if title.lower() in id_by_title:
                skipped += 1
                continue
            if count >= LIMITS["tasks"]:
                raise limit_reached(f"An event can have at most {LIMITS['tasks']} tasks")
            cur = ctx.db.execute(
                """INSERT INTO tasks (event_id, title, description, due_date, status, category, source,
                                      created_at, updated_at)
                   VALUES (?, ?, '', ?, 'todo', ?, 'template', ?, ?)""",
                (event["id"], title, add_days(event["event_date"], -days), category, ts, ts),
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
