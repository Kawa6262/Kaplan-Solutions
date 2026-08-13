"""Watchdog — erkennt wenn Outreach hängt, startet neu, holt nach, warnt per Mail."""

from __future__ import annotations

import os
import subprocess
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from outreach import config
from outreach import pacing
from outreach import sender
from outreach import storage
from outreach import system_state
from outreach.daily_health_check import _restart_daemon

try:
    from mailer import email_configured, send_email
except ImportError:
    email_configured = lambda: False  # type: ignore
    send_email = None  # type: ignore

TZ = ZoneInfo("Europe/Berlin")
REPORT_EMAIL = os.getenv(
    "OUTREACH_HEALTH_EMAIL", os.getenv("ADMIN_EMAIL", "")
).strip()

# Mindest-Versand bis zu dieser Stunde (Partner+Referral+Bauherr)
MIN_BY_HOUR = {
    10: 3,
    11: 8,
    12: 15,
    13: 22,
    14: 30,
    15: 40,
    16: 55,
    17: 70,
}


def _sent_today_total() -> int:
    return (
        storage.get_counter("sent", "partner")
        + storage.get_counter("sent", "referral")
        + storage.get_counter("sent", "bauherr")
    )


def _daily_limit_total() -> int:
    total = config.DAILY_SEND_LIMIT
    if config.REFERRAL_ENABLED:
        total += config.REFERRAL_DAILY_SEND_LIMIT
    if config.BAUHERR_ENABLED:
        total += config.BAUHERR_DAILY_SEND_LIMIT
    return total


def _min_expected(now: datetime) -> int:
    best = 0
    for hour, minimum in MIN_BY_HOUR.items():
        if now.hour >= hour:
            best = max(best, minimum)
    return best


def _cycle_stale(now: datetime) -> bool:
    last = system_state.last_cycle_ok()
    if last is None:
        return True
    return (now - last) > timedelta(minutes=25)


def _aggressive_catchup(max_rounds: int = 20) -> int:
    """Sendet so viel wie möglich bis Tageslimit oder Leerlauf."""
    total = 0
    for _ in range(max_rounds):
        if not pacing.in_send_window():
            break
        sent = sender.send_end_of_day_flush() if pacing.is_flush_window() else sender.send_batch(max_per_cycle=12)
        if sent <= 0:
            sent = sender.send_batch(max_per_cycle=12)
        if sent <= 0:
            break
        total += sent
        time.sleep(1)
    return total


def _send_watchdog_mail(subject: str, body: str) -> None:
    if not email_configured() or not REPORT_EMAIL or not send_email:
        print(f"[watchdog] {subject}\n{body}", flush=True)
        return
    html = f"<!DOCTYPE html><html><body style='font-family:Arial,sans-serif;line-height:1.7;max-width:560px;padding:24px'><pre style='white-space:pre-wrap;font-family:Arial,sans-serif'>{body}</pre></body></html>"
    send_email(REPORT_EMAIL, subject, body, html)  # type: ignore


def run_watchdog(*, force: bool = False) -> bool:
    now = datetime.now(TZ)
    if config.SEND_WEEKDAYS_ONLY and now.weekday() >= 5 and not force:
        print("[watchdog] Wochenende — übersprungen", flush=True)
        return True
    if not pacing.in_send_window() and not force:
        print("[watchdog] Außerhalb Sendefenster — übersprungen", flush=True)
        return True

    storage.init_db()
    sent = _sent_today_total()
    limit = _daily_limit_total()
    minimum = _min_expected(now)
    queued = storage.stats_summary()["queued"]
    stale = _cycle_stale(now)
    last = system_state.last_cycle_ok()
    last_s = last.strftime("%d.%m. %H:%M") if last else "nie"

    problem = stale or (minimum > 0 and sent < minimum and queued > 0)
    if not problem and not force:
        print(f"[watchdog] OK — {sent}/{limit} gesendet, letzter Zyklus {last_s}", flush=True)
        return True

    actions: list[str] = []
    if stale or sent < minimum:
        ok, note = _restart_daemon()
        actions.append(f"Daemon-Neustart: {note if ok else 'FEHLGESCHLAGEN'}")

    caught = _aggressive_catchup()
    if caught:
        actions.append(f"Nachholversand: +{caught} Mails")

    sent_after = _sent_today_total()
    still_bad = sent_after < minimum and queued > 0 and pacing.in_send_window()

    if still_bad:
        subject = f"🚨 Outreach hängt — {sent_after}/{limit} ({now.strftime('%d.%m. %H:%M')})"
        status = "ACHTUNG: Outreach hängt noch — Mac muss an sein + Netzteil."
    elif sent_after > sent:
        subject = f"⚠ Outreach repariert — jetzt {sent_after}/{limit} ({now.strftime('%d.%m. %H:%M')})"
        status = "Problem erkannt und automatisch behoben."
    else:
        subject = f"ℹ Outreach Watchdog ({now.strftime('%d.%m. %H:%M')})"
        status = "Watchdog aktiv — kein Handlungsbedarf."

    body = f"""Kaplan Solutions — Outreach Watchdog
{now.strftime('%d.%m.%Y %H:%M')}

{status}

Versendet heute:  {sent_after} / {limit} (vorher {sent})
Erwartet bis {now.hour}:00: mindestens {minimum}
Warteschlange:    {queued}
Letzter Zyklus:   {last_s}

Maßnahmen:
{chr(10).join('• ' + a for a in actions) if actions else '• Keine'}

Wichtig: Outreach läuft NUR wenn der Mac wach ist (Netzteil + Deckel zu OK).
Bei mehreren Tagen geschlossen ohne Strom: Versand pausiert bis zum Aufwachen.
"""
    _send_watchdog_mail(subject, body)
    print(f"[watchdog] {subject}", flush=True)
    return not still_bad
