"""Gleichmäßige Verteilung der Versände über das Sendefenster (8–18 Uhr)."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from outreach import config
from outreach import storage

TZ = ZoneInfo("Europe/Berlin")


def _cycles_left_in_window() -> int:
    now = datetime.now(TZ)
    end = now.replace(hour=config.SEND_HOUR_END, minute=0, second=0, microsecond=0)
    seconds_left = max(0, (end - now).total_seconds())
    return max(1, int(seconds_left // config.DAEMON_INTERVAL) + 1)


def paced_batch_cap(daily_limit: int, max_batch: int, campaign: str) -> int:
    """Max. Sends diesen Zyklus, damit das Tageslimit gleichmäßig über den Tag verteilt wird."""
    remaining = daily_limit - storage.get_counter("sent", campaign)
    if remaining <= 0:
        return 0
    cycles = _cycles_left_in_window()
    paced = (remaining + cycles - 1) // cycles
    return min(max(1, paced), max_batch, remaining)
