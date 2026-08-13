"""Letzter erfolgreicher Outreach-Zyklus (für Watchdog)."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from outreach import config

TZ = ZoneInfo("Europe/Berlin")
PATH = config.DATA_DIR / "last_cycle.ok"


def record_cycle_ok() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    PATH.write_text(datetime.now(TZ).isoformat(), encoding="utf-8")


def last_cycle_ok() -> datetime | None:
    if not PATH.is_file():
        return None
    try:
        raw = PATH.read_text(encoding="utf-8").strip()
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ)
        return dt.astimezone(TZ)
    except (OSError, ValueError):
        return None
