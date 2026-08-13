"""Erinnerungs-Mail Tag N — Formular für bessere Matching-Daten."""

from __future__ import annotations

import os
from zoneinfo import ZoneInfo

from outreach import storage
from outreach.email_layout import (
    TEXT,
    body_block,
    highlight_box,
    reply_hint_html,
    safe,
    text_footer,
    wrap_outreach_email,
)
from outreach.urls import bauherr_form_url, partner_form_url

REPLY = os.getenv("REPLY_EMAIL", "kontakt@kaplan-solutions.de").strip()

try:
    from mailer import email_configured, send_email
except ImportError:
    email_configured = lambda: False  # type: ignore
    send_email = None  # type: ignore

TZ = ZoneInfo("Europe/Berlin")
REMINDER_DAYS = int(os.getenv("OUTREACH_REMINDER_DAYS", "3"))
REMINDER_BATCH = int(os.getenv("OUTREACH_REMINDER_BATCH", "8"))


def _build_reminder(company: str, city: str, email: str, prospect_id: int | None = None) -> tuple[str, str]:
    region = city or "Ihrer Region"
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
{text_footer(email, "Geschäftliche Kontaktaufnahme gemäß § 7 Abs. 3 UWG (Bauleistungen).")}
"""

    bauherr_box = highlight_box(
        f'<strong style="color:{TEXT};">Kennen Sie Bauherren?</strong><br>'
        "Leiten Sie sie gern an unsere "
        f'<strong style="color:{TEXT};">kostenlose Vermittlung</strong> weiter — '
        f"für Bauherren entstehen keine Kosten:<br>"
        f'<a href="{safe(bauherr_link)}" style="color:{TEXT};text-decoration:none;font-weight:600;">'
        f"{safe(bauherr_link.replace('https://', ''))}</a>"
    )

    body_html = body_block(
        f'vor einigen Tagen hatten wir uns zu einer Partnerschaft bei '
        f'<strong style="color:{TEXT};">{safe(company)}</strong> ({safe(region)}) gemeldet.',
        "Falls noch Interesse besteht — mit dem Formular (ca. 2 Min.) ordnen wir Sie passenden Projekten zu.",
    ) + reply_hint_html() + bauherr_box

    html = wrap_outreach_email(
        headline=f"Rückfrage — {company}",
        eyebrow="Erinnerung",
        body_html=body_html,
        cta_label="Partner werden — 2 Min.",
        cta_url=form_url,
        recipient_email=email,
        legal="Geschäftliche Kontaktaufnahme gemäß § 7 Abs. 3 UWG (Bauleistungen).",
    )
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

    subject = f"Rückfrage — {company[:50]}"
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
