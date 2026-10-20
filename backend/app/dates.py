from __future__ import annotations

import re
from datetime import date, datetime, timedelta

_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def is_valid_date(value: object) -> bool:
    if not isinstance(value, str):
        return False
    m = _DATE_RE.match(value)
    if not m:
        return False
    y, mo, d = (int(g) for g in m.groups())
    if not 2000 <= y <= 2100:
        return False
    try:
        date(y, mo, d)
    except ValueError:
        return False
    return True


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def add_days(value: str, days: int) -> str:
    return (parse_date(value) + timedelta(days=days)).isoformat()


def days_between(start: str, end: str) -> int:
    return (parse_date(end) - parse_date(start)).days


def to_date_string(moment: datetime) -> str:
    return moment.date().isoformat()
