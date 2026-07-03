"""Gleichmäßige Verteilung der Versände über das Sendefenster (8–18 Uhr)."""

from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo

from outreach import config
from outreach import storage

TZ = ZoneInfo("Europe/Berlin")
FLUSH_HOUR = int(os.getenv("OUTREACH_FLUSH_HOUR", "17"))
ENRICH_CUTOFF_HOUR = int(os.getenv("OUTREACH_ENRICH_CUTOFF_HOUR", "17"))


def _now() -> datetime:
    return datetime.now(TZ)


def _cycles_left_in_window() -> int:
    now = _now()
    end = now.replace(hour=config.SEND_HOUR_END, minute=0, second=0, microsecond=0)
    seconds_left = max(0, (end - now).total_seconds())
    return max(1, int(seconds_left // config.DAEMON_INTERVAL) + 1)


def in_send_window() -> bool:
    """Strikt: keine Versände ab SEND_HOUR_END (z. B. 18:00)."""
    now = _now()
    if config.SEND_WEEKDAYS_ONLY and now.weekday() >= 5:
        return False
    if now.hour < config.SEND_HOUR_START:
        return False
    if now.hour >= config.SEND_HOUR_END:
        return False
    return True


def enrich_allowed() -> bool:
    """Keine neuen queued-Kontakte nach 17 Uhr — gehen sonst erst am nächsten Tag raus."""
    now = _now()
    if config.SEND_WEEKDAYS_ONLY and now.weekday() >= 5:
        return False
    return now.hour < ENRICH_CUTOFF_HOUR


def is_flush_window() -> bool:
    """Ab 17:00: Rest-Kontingent vor Fensterende raus, damit nichts liegen bleibt."""
    now = _now()
    if not in_send_window() and now.hour < config.SEND_HOUR_END:
        return False
    if now.hour >= config.SEND_HOUR_END:
        return False
    return now.hour >= FLUSH_HOUR


def paced_batch_cap(daily_limit: int, max_batch: int, campaign: str) -> int:
    """Max. Sends diesen Zyklus — im Flush-Fenster ohne Drosselung."""
    remaining = daily_limit - storage.get_counter("sent", campaign)
    if remaining <= 0:
        return 0
    if is_flush_window():
        return min(remaining, max_batch * 3, remaining)
    cycles = _cycles_left_in_window()
    paced = (remaining + cycles - 1) // cycles
    return min(max(1, paced), max_batch, remaining)
