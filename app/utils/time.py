from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

BISHKEK_TZ = ZoneInfo("Asia/Bishkek")


def now_bishkek() -> datetime:
    return datetime.now(tz=BISHKEK_TZ)


def bishkek_today() -> date:
    return now_bishkek().date()


def bishkek_day_bounds(d: date) -> tuple[datetime, datetime]:
    """
    Returns [start, end) bounds for given date in Asia/Bishkek timezone.
    """
    start = datetime.combine(d, time.min, tzinfo=BISHKEK_TZ)
    end = start + timedelta(days=1)
    return start, end
