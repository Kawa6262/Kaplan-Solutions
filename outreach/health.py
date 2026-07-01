"""System-Gesundheit: Fehler zählen, Admin warnen, DB reparieren."""

from __future__ import annotations

import os
import sqlite3
import time
from datetime import date, datetime
from zoneinfo import ZoneInfo

from outreach import config
from outreach import storage

try:
    from mailer import email_configured, send_email
except ImportError:
    email_configured = lambda: False  # type: ignore
    send_email = None  # type: ignore

ALERT_EMAIL = os.getenv("OUTREACH_ALERT_EMAIL", os.getenv("ADMIN_EMAIL", "")).strip()
ERROR_THRESHOLD = int(os.getenv("OUTREACH_ERROR_ALERT_THRESHOLD", "3"))
ALERT_COOLDOWN_SEC = int(os.getenv("OUTREACH_ERROR_ALERT_COOLDOWN", "3600"))

_consecutive_errors = 0
_last_alert_at: float = 0.0


def record_success() -> None:
    global _consecutive_errors
    _consecutive_errors = 0


def record_error(exc: Exception) -> None:
    global _consecutive_errors, _last_alert_at
    _consecutive_errors += 1
    if _consecutive_errors < ERROR_THRESHOLD:
        return
    now = time.time()
    if now - _last_alert_at < ALERT_COOLDOWN_SEC:
        return
    _last_alert_at = now
    _send_alert(exc)


def recover_db() -> None:
    """WAL checkpoint + Verbindung zurücksetzen nach I/O-Fehlern."""
    storage.reset_connection()
    try:
        storage.wal_checkpoint()
        storage.init_db()
        record_success()
    except Exception as exc:
        print(f"[outreach] DB-Recovery fehlgeschlagen: {exc}", flush=True)


def _send_alert(exc: Exception) -> None:
    if not email_configured() or not ALERT_EMAIL or send_email is None:
        return
    today = date.today().isoformat()
    if storage.alert_was_sent(today):
        return
    subject = f"⚠️ Outreach-Alarm · {datetime.now(ZoneInfo('Europe/Berlin')).strftime('%d.%m. %H:%M')}"
    text = f"""Kaplan Solutions Outreach — Systemwarnung

{_consecutive_errors} aufeinanderfolgende Fehler:
{exc}

Automatische DB-Wiederherstellung wurde ausgelöst.
Bitte prüfen, ob der Mac wach ist und der Daemon läuft:
  launchctl list | grep kaplan

Log: {config.LOG_PATH}
"""
    try:
        send_email(ALERT_EMAIL, subject, text, f"<pre>{text}</pre>")  # type: ignore
        storage.mark_alert_sent(today)
        print(f"[outreach] ⚠ Alarm-Mail → {ALERT_EMAIL}", flush=True)
    except Exception as mail_exc:
        print(f"[outreach] Alarm-Mail fehlgeschlagen: {mail_exc}", flush=True)


def is_sqlite_io_error(exc: BaseException) -> bool:
    if not isinstance(exc, sqlite3.OperationalError):
        return False
    msg = str(exc).lower()
    return "disk i/o" in msg or "unable to open" in msg or "database is locked" in msg
