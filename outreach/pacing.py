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


# Gewichtung je Stunde: Sekretariate und Büros sichten die Post am frühen Morgen,
# deshalb geht der Großteil bis 11 Uhr raus. Der Rest hält den Tag über nach.
_HOUR_WEIGHTS = {7: 16, 8: 20, 9: 18, 10: 13, 11: 9, 12: 5, 13: 4, 14: 4, 15: 4, 16: 4, 17: 3}


def _target_fraction() -> float:
    """Anteil des Tageskontingents, der zum jetzigen Zeitpunkt raus sein soll."""
    now = _now()
    hours = range(config.SEND_HOUR_START, config.SEND_HOUR_END)
    total = sum(_HOUR_WEIGHTS.get(h, 1) for h in hours)
    if total <= 0:
        return 1.0
    done = sum(_HOUR_WEIGHTS.get(h, 1) for h in hours if h < now.hour)
    if now.hour in hours:
        done += _HOUR_WEIGHTS.get(now.hour, 1) * (now.minute / 60)
    return min(1.0, done / total)


def paced_batch_cap(daily_limit: int, max_batch: int, campaign: str) -> int:
    """Max. Sends diesen Zyklus — vormittagslastig, im Flush-Fenster ohne Drosselung."""
    sent = storage.get_counter("sent", campaign)
    remaining = daily_limit - sent
    if remaining <= 0:
        return 0
    if is_flush_window():
        return min(remaining, max_batch * 3)
    target = -(-int(daily_limit * _target_fraction() * 100) // 100)  # aufrunden
    allowed = target - sent
    if allowed <= 0:
        return 0
    return min(allowed, max_batch, remaining)
