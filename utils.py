import os
from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:
    TIMEZONE = ZoneInfo(os.environ.get("APP_TIMEZONE", "America/New_York"))
except ZoneInfoNotFoundError:
    TIMEZONE = None  # fall back to the computer's own clock


def local_now():
    """Current local time as a naive datetime, comparable to the times hosts enter."""
    if TIMEZONE is None:
        return datetime.now()
    return datetime.now(TIMEZONE).replace(tzinfo=None)


def age_from(birthdate, today=None):
    today = today or local_now().date()
    return today.year - birthdate.year - (
        (today.month, today.day) < (birthdate.month, birthdate.day)
    )