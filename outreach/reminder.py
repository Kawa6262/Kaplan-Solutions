"""Erinnerungs-Mail Tag N — Formular für bessere Matching-Daten."""

from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo

from outreach import storage
from company_config import company_footer_text
from email_deliverability import public_site_url, unsubscribe_url
from outreach.urls import bauherr_form_url, partner_form_url

SITE = public_site_url()
REPLY = os.getenv("REPLY_EMAIL", "kontakt@kaplan-solutions.de").strip()

try:
    from mailer import email_configured, send_email
except ImportError:
    email_configured = lambda: False  # type: ignore
    send_email = None  # type: ignore

TZ = ZoneInfo("Europe/Berlin")
REMINDER_DAYS = int(os.getenv("OUTREACH_REMINDER_DAYS", "3"))
REMINDER_BATCH = int(os.getenv("OUTREACH_REMINDER_BATCH", "8"))


def _safe(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _build_reminder(company: str, city: str, email: str, prospect_id: int | None = None) -> tuple[str, str]:
    region = city or "Ihrer Region"
    unsub = unsubscribe_url(email)
    form_url = partner_form_url(prospect_id)
    bauherr_link = bauherr_form_url(prospect_id)
    text = f"""Sehr geehrte Damen und Herren,

vor einigen Tagen hatten wir uns kurz zu einer Partnerschaft im Baunetzwerk von Kaplan Solutions gemeldet ({company}, {region}).

Falls Sie noch Interesse haben — Partner werden (2 Min., voreingestellt):
{form_url}

Noch einfacher: Antworten Sie mit „Interesse" auf diese E-Mail.

Kennen Sie Bauherren? Kostenlose Vermittlung für Mandanten:
{bauherr_link}

Mit freundlichen Grüßen
Kaplan Solutions

{company_footer_text()}
{SITE}

Abmelden: {unsub}
"""
    html = f"""<!DOCTYPE html><html lang="de"><body style="font-family:Arial,sans-serif;color:#333;line-height:1.6">
<p>Sehr geehrte Damen und Herren,</p>
<p>vor einigen Tagen hatten wir uns zu einer Partnerschaft bei <strong>{_safe(company)}</strong> ({_safe(region)}) gemeldet.</p>
<p>Falls noch Interesse besteht — mit dem Formular (3 Min.) ordnen wir Sie passenden Projekten zu:</p>
<p><a href="{_safe(form_url)}" style="background:#0b3d2e;color:#fff;padding:12px 20px;text-decoration:none;border-radius:2px">Partner werden — 2 Min.</a></p>
<p style="font-size:13px;color:#666">Oder mit <strong>„Interesse"</strong> auf diese E-Mail antworten.</p>
<p style="font-size:12px;color:#888"><a href="{_safe(unsub)}">Abmelden</a></p>
<p style="margin-top:24px;padding-top:20px;border-top:1px solid #eee">
  <strong>Kennen Sie Bauherren?</strong><br>
  Leiten Sie sie gern an unsere <strong>kostenlose Vermittlung</strong> weiter — für Bauherren entstehen keine Kosten:<br>
  <a href="{_safe(bauherr_link)}">{_safe(bauherr_link)}</a>
</p>
<p>Mit freundlichen Grüßen<br><strong>Kaplan Solutions</strong></p>
</body></html>"""
    return text, html


def send_one_reminder(row) -> bool:
    if not email_configured() or not send_email:
        return False
    email = (row["email"] or "").strip()
    company = row["company_name"] or "Ihr Unternehmen"
    city = row["city"] or ""
    if storage.is_unsubscribed(email):
        storage.mark_reminder_sent(int(row["id"]))
        return False

    subject = f"Kaplan Solutions — noch Interesse, {company}?"
    text, html = _build_reminder(company, city, email, int(row["id"]))
    try:
        send_email(
            email,
            subject,
            text,
            html,
            reply_to=REPLY,
            tags=[{"name": "category", "value": "outreach_reminder"}],
        )
        storage.mark_reminder_sent(int(row["id"]))
        print(f"[outreach] ↻ Erinnerung → {company} <{email}>", flush=True)
        return True
    except Exception as exc:
        print(f"[outreach] Erinnerung fehlgeschlagen {company}: {exc}", flush=True)
        return False


def process_reminders() -> int:
    if not email_configured():
        return 0
    sent = 0
    for row in storage.due_for_reminder(days=REMINDER_DAYS, limit=REMINDER_BATCH):
        if send_one_reminder(row):
            sent += 1
    return sent
