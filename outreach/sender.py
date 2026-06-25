"""Versandlogik mit Tageslimit und Geschäftszeiten."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from outreach import config
from outreach import storage
from outreach.templates import build_bodies, build_subject

try:
    from mailer import email_configured, send_email
except ImportError:
    email_configured = lambda: False  # type: ignore
    send_email = None  # type: ignore


def _in_send_window() -> bool:
    now = datetime.now(ZoneInfo("Europe/Berlin"))
    if config.SEND_WEEKDAYS_ONLY and now.weekday() >= 5:
        return False
    return config.SEND_HOUR_START <= now.hour < config.SEND_HOUR_END


def send_one() -> bool:
    """Sendet maximal eine E-Mail. Returns True wenn gesendet."""
    if not email_configured():
        print("[outreach] E-Mail nicht konfiguriert (RESEND_API_KEY + ADMIN_EMAIL).", flush=True)
        return False
    if not _in_send_window():
        return False
    if storage.get_counter("sent") >= config.DAILY_SEND_LIMIT:
        return False

    row = storage.next_to_send()
    if not row:
        return False

    email = (row["email"] or "").strip()
    company = row["company_name"] or "Ihr Unternehmen"
    city = row["city"] or ""
    trade = row["trade"] or "Bau"

    if storage.is_unsubscribed(email):
        storage.mark_enriched(row["id"], email, "unsubscribed")
        return False

    subject = build_subject(company, city)
    text_body, html_body = build_bodies(company, city, trade)

    try:
        send_email(email, subject, text_body, html_body)  # type: ignore
        storage.mark_sent(row["id"])
        storage.bump_counter("sent")
        print(f"[outreach] ✓ Gesendet an {company} <{email}>", flush=True)
        return True
    except Exception as exc:
        storage.mark_failed(row["id"], str(exc))
        print(f"[outreach] ✗ Fehler {company}: {exc}", flush=True)
        return False
