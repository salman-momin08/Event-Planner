from __future__ import annotations

from typing import Literal, get_args

MAX_CENTS = 1_000_000_000
Currency = Literal["USD", "EUR", "GBP", "INR", "AUD", "CAD", "SGD", "NZD", "CHF", "AED"]
CURRENCIES = get_args(Currency)


def percent_to_cents(total_cents: int, percent: float) -> int:
    """Integer basis points avoid float error; result is floored."""
    basis_points = round(percent * 100)
    return (total_cents * basis_points) // 10000


def cents_to_decimal(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    whole, frac = divmod(abs(cents), 100)
    return f"{sign}{whole}.{frac:02d}"
