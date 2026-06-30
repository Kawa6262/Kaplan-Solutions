"""Versandlogik mit Tageslimit und Geschäftszeiten."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import os

from outreach import config
from outreach import storage
from outreach.templates import build_bodies, build_subject
from outreach.referral_templates import build_bodies as build_referral_bodies
from outreach.referral_templates import build_subject as build_referral_subject
from outreach.bauherr_templates import build_bodies as build_bauherr_bodies
from outreach.bauherr_templates import build_subject as build_bauherr_subject

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


def _send_limits(campaign: str) -> tuple[int, str]:
    if campaign == config.CAMPAIGN_REFERRAL:
        return config.REFERRAL_DAILY_SEND_LIMIT, "referral_outreach"
    if campaign == config.CAMPAIGN_BAUHERR:
        return config.BAUHERR_DAILY_SEND_LIMIT, "bauherr_outreach"
    return config.DAILY_SEND_LIMIT, "outreach"


def send_one(campaign: str = config.CAMPAIGN_PARTNER) -> bool:
    """Sendet maximal eine E-Mail. Returns True wenn gesendet."""
    if campaign == config.CAMPAIGN_REFERRAL and not config.REFERRAL_ENABLED:
        return False
    if campaign == config.CAMPAIGN_BAUHERR and not config.BAUHERR_ENABLED:
        return False
    if not email_configured():
        print("[outreach] E-Mail nicht konfiguriert (RESEND_API_KEY + ADMIN_EMAIL).", flush=True)
        return False
    if not _in_send_window():
        return False

    daily_limit, tag = _send_limits(campaign)
    if storage.get_counter("sent", campaign) >= daily_limit:
        return False

    row = storage.next_to_send(campaign)
    if not row:
        return False

    email = (row["email"] or "").strip()
    company = row["company_name"] or "Ihr Unternehmen"
    city = row["city"] or ""
    trade = row["trade"] or "Bau"

    if storage.is_unsubscribed(email):
        storage.mark_enriched(row["id"], email, "unsubscribed")
        return False

    if campaign == config.CAMPAIGN_REFERRAL:
        subject = build_referral_subject(company, city)
        text_body, html_body = build_referral_bodies(
            company, city, trade, recipient_email=email
        )
        label = "Referral"
    elif campaign == config.CAMPAIGN_BAUHERR:
        subject = build_bauherr_subject(company, city)
        text_body, html_body = build_bauherr_bodies(
            company, city, trade, recipient_email=email
        )
        label = "Bauherr"
    else:
        subject = build_subject(company, city)
        text_body, html_body = build_bodies(company, city, trade, recipient_email=email)
        label = "Partner"

    reply_to = os.getenv("REPLY_EMAIL", "kontakt@kaplan-solutions.de").strip()

    try:
        send_email(
            email,
            subject,
            text_body,
            html_body,
            reply_to=reply_to,
            tags=[{"name": "category", "value": tag}],
        )  # type: ignore
        storage.mark_sent(row["id"])
        storage.bump_counter("sent", campaign=campaign)
        print(f"[outreach] ✓ {label} → {company} <{email}>", flush=True)
        if campaign == config.CAMPAIGN_PARTNER:
            try:
                from outreach import sheet_sync

                sheet_sync.sync_prospect(row)
            except Exception as exc:
                print(f"[outreach] Sheet-Sync übersprungen: {exc}", flush=True)
        return True
    except Exception as exc:
        storage.mark_failed(row["id"], str(exc))
        print(f"[outreach] ✗ Fehler {company}: {exc}", flush=True)
        return False


def send_batch(max_per_cycle: int | None = None) -> int:
    """Sendet Partner- und Referral-Mails pro Zyklus (bis Tageslimit)."""
    cap = max_per_cycle if max_per_cycle is not None else config.SEND_BATCH_PER_CYCLE
    sent = 0
    for _ in range(max(1, cap)):
        if send_one(config.CAMPAIGN_PARTNER):
            sent += 1
        else:
            break

    if config.REFERRAL_ENABLED:
        ref_cap = config.REFERRAL_SEND_BATCH_PER_CYCLE
        for _ in range(max(1, ref_cap)):
            if send_one(config.CAMPAIGN_REFERRAL):
                sent += 1
            else:
                break

    if config.BAUHERR_ENABLED:
        bh_cap = config.BAUHERR_SEND_BATCH_PER_CYCLE
        for _ in range(max(1, bh_cap)):
            if send_one(config.CAMPAIGN_BAUHERR):
                sent += 1
            else:
                break
    return sent
