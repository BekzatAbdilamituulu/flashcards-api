from __future__ import annotations

from datetime import date, timedelta

def month_bounds(year: int, month: int) -> tuple[date, date]:
    """
    Returns (first_day, last_day) inclusive for a given month.
    """
    if month < 1 or month > 12:
        raise ValueError("month must be 1..12")

    first = date(year, month, 1)
    # next month first day
    if month == 12:
        next_first = date(year + 1, 1, 1)
    else:
        next_first = date(year, month + 1, 1)

    last = next_first - timedelta(days=1)
    return first, last