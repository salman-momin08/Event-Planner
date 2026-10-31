from __future__ import annotations

import sqlite3

from ..context import Context
from ..db import transaction, update_row
from ..errors import limit_reached, not_found
from ..schemas import ScheduleItemIn, ScheduleItemPatch

MAX_SCHEDULE_ITEMS = 120

COLUMNS = {
    "startTime": "start_time",
    "durationMinutes": "duration_minutes",
    "title": "title",
    "locationZone": "location_zone",
    "owner": "owner",
    "notes": "notes",
}

# Event-day Run-of-Show templates: (start_time, duration_minutes, title, location_zone, owner, notes)
RUN_OF_SHOW_TEMPLATES = {
    "wedding": [
        ("14:00", 90, "Venue access, floral & lighting setup", "Main Hall & Garden", "Decor Lead", "Verify backup power and stage lighting"),
        ("15:30", 60, "Soundcheck & AV walkthrough", "Stage / Ceremony Arch", "DJ / AV Team", "Test wireless microphones and entrance cue music"),
        ("16:30", 45, "Guest arrival & welcome refreshments", "Entrance Foyer", "Hospitality Host", "Acoustic playlist and welcome signage placed"),
        ("17:15", 60, "Main ceremony", "Ceremony Lawn", "Officiant & Coordinator", "Processional cue 5 mins prior"),
        ("18:15", 60, "Cocktail hour & group portraits", "Garden Terrace", "Photographer", "Pass hors d'oeuvres and Mocktail/Cocktail service"),
        ("19:15", 90, "Grand entrance, toasts & dinner service", "Banquet Hall", "Catering Lead & MC", "Confirm dietary plates for VIP and allergy tables"),
        ("20:45", 90, "Cake cutting & open dance floor", "Main Stage", "DJ / Entertainment", "Transition lighting to party mood"),
        ("22:15", 45, "Farewell send-off & venue load-out", "Main Exit", "Event Coordinator", "Collect gifts, personal decor items, and vendor sign-off"),
    ],
    "birthday": [
        ("16:30", 60, "Decor, balloon arch & dessert table setup", "Party Area", "Host / Decorator", "Set up photo booth backdrop and lighting"),
        ("17:30", 30, "Music check & welcome drinks prep", "Lounge & Bar", "Host", "Queue upbeat welcome playlist"),
        ("18:00", 45, "Guest arrival & welcome snacks", "Main Room", "Host", "Instant polaroids / guestbook station"),
        ("18:45", 45, "Interactive games & group activities", "Activity Zone", "Game Host / MC", "Keep prizes ready"),
        ("19:30", 30, "Cake cutting, toast & group photos", "Dessert Stage", "Host & Photographer", "Dim lights, sparkler candles ready"),
        ("20:00", 75, "Dinner service & music", "Dining Area", "Catering", "Serve vegetarian and kids options first"),
        ("21:15", 45, "Return favours & wrap-up", "Entrance", "Host", "Hand out party favour bags"),
    ],
    "community": [
        ("08:30", 60, "Site safety walk, signage & registration desk setup", "Main Gate", "Site Lead", "Check emergency exits, first-aid kit, and accessibility ramps"),
        ("09:30", 30, "Volunteer & speaker briefing", "Main Stage", "Volunteer Coordinator", "Distribute lanyards and radio channels"),
        ("10:00", 45, "Doors open, check-in & networking coffee", "Registration Plaza", "Check-in Team", "Scan registrations and hand out schedules"),
        ("10:45", 60, "Opening keynote & community announcements", "Main Auditorium", "MC & Keynote Speaker", "Live captions and mic runner ready"),
        ("11:45", 75, "Breakout sessions / workshops & booths", "Breakout Rooms", "Track Leads", "10-minute warning chime before rotation"),
        ("13:00", 60, "Community lunch & sponsor showcase", "Courtyard", "Catering & Volunteers", "Clearly label vegan, vegetarian, and allergen-free stations"),
        ("14:00", 60, "Panel discussion & Q&A", "Main Auditorium", "Moderator", "Collect audience questions"),
        ("15:00", 30, "Closing remarks, thank-yous & site teardown", "Main Auditorium", "Event Lead", "Recycle badges and clear signage"),
    ],
}


def _end_time(start_time: str, duration_minutes: int) -> str:
    hh, mm = map(int, start_time.split(":"))
    total = (hh * 60 + mm + duration_minutes) % (24 * 60)
    return f"{total // 60:02d}:{total % 60:02d}"


def _item(r: sqlite3.Row) -> dict:
    return {
        "id": r["id"],
        "startTime": r["start_time"],
        "endTime": _end_time(r["start_time"], r["duration_minutes"]),
        "durationMinutes": r["duration_minutes"],
        "title": r["title"],
        "locationZone": r["location_zone"],
        "owner": r["owner"],
        "notes": r["notes"],
    }


def list_schedule(ctx: Context, event_id: int) -> list[dict]:
    rows = ctx.db.execute(
        "SELECT * FROM schedule_items WHERE event_id = ? ORDER BY start_time ASC, id ASC",
        (event_id,),
    ).fetchall()
    return [_item(r) for r in rows]


def _get(ctx: Context, event_id: int, item_id: int) -> dict:
    row = ctx.db.execute("SELECT * FROM schedule_items WHERE id = ? AND event_id = ?", (item_id, event_id)).fetchone()
    if row is None:
        raise not_found("Schedule item")
    return _item(row)


def create_schedule_item(ctx: Context, event_id: int, body: ScheduleItemIn) -> dict:
    n = ctx.db.execute("SELECT COUNT(*) AS n FROM schedule_items WHERE event_id = ?", (event_id,)).fetchone()["n"]
    if n >= MAX_SCHEDULE_ITEMS:
        raise limit_reached(f"An event can have at most {MAX_SCHEDULE_ITEMS} run-of-show items")
    cur = ctx.db.execute(
        """INSERT INTO schedule_items (event_id, start_time, duration_minutes, title, location_zone, owner, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (event_id, body.startTime, body.durationMinutes, body.title, body.locationZone, body.owner, body.notes),
    )
    return _get(ctx, event_id, int(cur.lastrowid))


def update_schedule_item(ctx: Context, event_id: int, item_id: int, body: ScheduleItemPatch) -> dict:
    _get(ctx, event_id, item_id)
    update_row(
        ctx.db,
        "schedule_items",
        COLUMNS,
        body.model_dump(exclude_unset=True),
        "id = ? AND event_id = ?",
        (item_id, event_id),
    )
    return _get(ctx, event_id, item_id)


def delete_schedule_item(ctx: Context, event_id: int, item_id: int) -> None:
    _get(ctx, event_id, item_id)
    ctx.db.execute("DELETE FROM schedule_items WHERE id = ? AND event_id = ?", (item_id, event_id))


def generate_default_schedule(ctx: Context, event: sqlite3.Row) -> dict:
    event_id = event["id"]
    template = RUN_OF_SHOW_TEMPLATES.get(event["type"], RUN_OF_SHOW_TEMPLATES["community"])
    with transaction(ctx.db):
        existing_rows = ctx.db.execute("SELECT title FROM schedule_items WHERE event_id = ?", (event_id,)).fetchall()
        existing_titles = {r["title"].lower() for r in existing_rows}
        count = len(existing_titles)
        created = skipped = 0
        for start_time, duration, title, zone, owner, notes in template:
            if title.lower() in existing_titles:
                skipped += 1
                continue
            if count >= MAX_SCHEDULE_ITEMS:
                raise limit_reached(f"An event can have at most {MAX_SCHEDULE_ITEMS} run-of-show items")
            ctx.db.execute(
                """INSERT INTO schedule_items (event_id, start_time, duration_minutes, title, location_zone, owner, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (event_id, start_time, duration, title, zone, owner, notes),
            )
            existing_titles.add(title.lower())
            count += 1
            created += 1
    return {"created": created, "skipped": skipped}
