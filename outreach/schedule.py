"""Gemeinsame Zeitplan-Logik für geplante Reports — mit Catch-up nach Sleep."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from outreach import config

TZ = ZoneInfo("Europe/Berlin")


def berlin_now() -> datetime:
    return datetime.now(TZ)


def is_business_day(now: datetime | None = None) -> bool:
    now = now or berlin_now()
    if config.SEND_WEEKDAYS_ONLY and now.weekday() >= 5:
        return False
    return True


def should_send_at_hour(target_hour: int, already_sent: bool) -> bool:
    """
    Sendet ab target_hour einmal täglich — auch wenn der Daemon die exakte
    Stunde verpasst hat (Sleep, SQLite-Fehler, Neustart).
    """
    if already_sent:
        return False
    if not is_business_day():
        return False
    return berlin_now().hour >= target_hour
