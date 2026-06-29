"""Zuverlässigkeit: Mac wach halten, Nachholversand nach Sleep/Pause."""

from __future__ import annotations

import subprocess
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from outreach import config
from outreach import sender
from outreach import storage

TZ = ZoneInfo("Europe/Berlin")


def _log(msg: str) -> None:
    print(f"[outreach] {msg}", flush=True)


def keep_awake_for_cycle() -> None:
    """Verhindert Sleep während des Sendefensters (Mo–Fr 9–18)."""
    if not config.CAFFEINATE_ENABLED:
        return
    if not sender._in_send_window():
        return
    duration = max(120, config.DAEMON_INTERVAL + 90)
    try:
        subprocess.Popen(
            [
                "caffeinate",
                "-i",  # idle sleep
                "-m",  # disk sleep
                "-s",  # system sleep (Netzteil)
                "-t",
                str(duration),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        _log("caffeinate nicht gefunden — Sleep-Schutz deaktiviert")


def catch_up_after_gap(gap_seconds: float) -> int:
    """
    Nach Sleep oder langer Pause fehlende Versand-Zyklen nachholen.
    Läuft nur innerhalb des Sendefensters und bis zum Tageslimit.
    """
    if not config.WAKE_CATCHUP_ENABLED:
        return 0
    if gap_seconds < config.DAEMON_INTERVAL * 1.5:
        return 0
    if not sender._in_send_window():
        return 0

    remaining = config.DAILY_SEND_LIMIT - storage.get_counter("sent")
    if remaining <= 0:
        return 0

    missed_cycles = max(1, int(gap_seconds // config.DAEMON_INTERVAL))
    # Normaler Zyklus sendet bereits SEND_BATCH — nur Mehrbedarf nachholen
    extra_budget = min(
        remaining,
        max(0, missed_cycles * config.SEND_BATCH_PER_CYCLE - config.SEND_BATCH_PER_CYCLE),
    )
    if extra_budget <= 0:
        return 0

    gap_min = gap_seconds / 60
    _log(
        f"Aufwach-Nachholung: {gap_min:.0f} Min. Pause → "
        f"bis zu {extra_budget} zusätzliche Mails"
    )

    total = 0
    while total < extra_budget:
        batch = min(config.SEND_BATCH_PER_CYCLE, extra_budget - total)
        sent = sender.send_batch(max_per_cycle=batch)
        if sent == 0:
            break
        total += sent
        time.sleep(1)
    if total:
        _log(f"Aufwach-Nachholung abgeschlossen: {total} Mails")
    return total


def in_send_window_now() -> bool:
    return sender._in_send_window()


def window_status_line() -> str:
    now = datetime.now(TZ)
    wd = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")[now.weekday()]
    active = "aktiv" if in_send_window_now() else "inaktiv"
    return (
        f"{wd} {now.strftime('%H:%M')} · Sendefenster {active} "
        f"({config.SEND_HOUR_START}:00–{config.SEND_HOUR_END}:00)"
    )
