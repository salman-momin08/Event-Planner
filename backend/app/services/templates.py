from __future__ import annotations

import sqlite3

from ..context import Context
from ..dates import add_days
from ..db import transaction
from ..errors import limit_reached
from .tasks import LIMITS, list_tasks

# (title, category, days before the event)
WEDDING = [
    ("Set budget and guest-count estimate", "Planning", 365),
    ("Book venue", "Venue", 330),
    ("Book photographer/videographer", "Photography", 300),
    ("Book caterer", "Catering", 270),
    ("Book officiant and music/DJ", "Entertainment", 240),
    ("Choose attire", "Attire", 210),
    ("Send save-the-dates", "Guests", 180),
    ("Book decor and florist", "Decor", 150),
    ("Send invitations", "Guests", 90),
    ("Finalise menu and cake", "Catering", 60),
    ("Confirm RSVPs and seating plan", "Guests", 21),
    ("Confirm all vendors and timeline", "Vendors", 14),
    ("Final payments", "Budget", 7),
    ("Rehearsal", "Ceremony", 1),
]
BIRTHDAY = [
    ("Set budget and guest list", "Planning", 42),
    ("Choose date and venue", "Venue", 35),
    ("Pick theme", "Theme", 28),
    ("Send invitations", "Guests", 21),
    ("Order cake", "Catering", 14),
    ("Plan food and drinks", "Catering", 10),
    ("Buy decorations and party favours", "Decor", 7),
    ("Plan activities and music", "Entertainment", 5),
    ("Confirm RSVPs", "Guests", 3),
    ("Set up venue", "Venue", 0),
]
COMMUNITY = [
    ("Define goals, budget and volunteer needs", "Planning", 120),
    ("Secure permits and insurance", "Compliance", 100),
    ("Book venue or site", "Venue", 90),
    ("Recruit volunteers", "Volunteers", 75),
    ("Book vendors and equipment", "Vendors", 60),
    ("Launch promotion", "Marketing", 45),
    ("Confirm sponsors and donations", "Budget", 30),
    ("Create run-of-show and volunteer schedule", "Logistics", 14),
    ("Safety and accessibility walkthrough", "Compliance", 7),
    ("Final briefing with volunteers", "Volunteers", 1),
    ("Post-event thanks and debrief", "Follow-up", -3),
]
TEMPLATES = {"wedding": WEDDING, "birthday": BIRTHDAY, "community": COMMUNITY}


def generate_timeline(ctx: Context, event: sqlite3.Row) -> dict:
    with transaction(ctx.db):
        existing = {t["title"].lower() for t in list_tasks(ctx, event["id"])}
        count = len(existing)
        created = skipped = 0
        ts = ctx.clock().isoformat()
        for title, category, days in TEMPLATES[event["type"]]:
            if title.lower() in existing:
                skipped += 1
                continue
            if count >= LIMITS["tasks"]:
                raise limit_reached(f"An event can have at most {LIMITS['tasks']} tasks")
            ctx.db.execute(
                """INSERT INTO tasks (event_id, title, description, due_date, status, category, source,
                                      created_at, updated_at)
                   VALUES (?, ?, '', ?, 'todo', ?, 'template', ?, ?)""",
                (event["id"], title, add_days(event["event_date"], -days), category, ts, ts),
            )
            count += 1
            created += 1
    return {"created": created, "skipped": skipped}
