"""Versandlogik mit Tageslimit und Geschäftszeiten."""

from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo

from outreach import config
from outreach import pacing
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
    return pacing.in_send_window()


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

    pid = int(row["id"])
    if campaign == config.CAMPAIGN_REFERRAL:
        subject = build_referral_subject(company, city)
        text_body, html_body = build_referral_bodies(
            company, city, trade, recipient_email=email, prospect_id=pid
        )
        label = "Referral"
    elif campaign == config.CAMPAIGN_BAUHERR:
        subject = build_bauherr_subject(company, city)
        text_body, html_body = build_bauherr_bodies(
            company, city, trade, recipient_email=email, prospect_id=pid
        )
        label = "Bauherr"
    else:
        subject = build_subject(company, city)
        text_body, html_body = build_bodies(
            company, city, trade, recipient_email=email, prospect_id=pid
        )
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


def _send_campaign_burst(campaign: str, cap: int) -> int:
    sent = 0
    for _ in range(max(0, cap)):
        if not _in_send_window():
            break
        if send_one(campaign):
            sent += 1
        else:
            break
    return sent


def send_batch(max_per_cycle: int | None = None) -> int:
    """Sendet Partner-, Referral- und Bauherr-Mails gleichmäßig über den Tag verteilt."""
    if not _in_send_window():
        return 0

    if pacing.is_flush_window() and max_per_cycle is None:
        return send_end_of_day_flush()

    if max_per_cycle is not None:
        cap = ref_cap = bh_cap = max_per_cycle
    else:
        cap = pacing.paced_batch_cap(
            config.DAILY_SEND_LIMIT, config.SEND_BATCH_PER_CYCLE, config.CAMPAIGN_PARTNER
        )
        ref_cap = pacing.paced_batch_cap(
            config.REFERRAL_DAILY_SEND_LIMIT,
            config.REFERRAL_SEND_BATCH_PER_CYCLE,
            config.CAMPAIGN_REFERRAL,
        )
        bh_cap = pacing.paced_batch_cap(
            config.BAUHERR_DAILY_SEND_LIMIT,
            config.BAUHERR_SEND_BATCH_PER_CYCLE,
            config.CAMPAIGN_BAUHERR,
        )

    sent = _send_campaign_burst(config.CAMPAIGN_PARTNER, cap)

    if config.REFERRAL_ENABLED:
        sent += _send_campaign_burst(config.CAMPAIGN_REFERRAL, ref_cap)

    if config.BAUHERR_ENABLED:
        sent += _send_campaign_burst(config.CAMPAIGN_BAUHERR, bh_cap)

    return sent


def send_end_of_day_flush() -> int:
    """17:00–18:00: verbleibendes Tageskontingent leeren (nie nach 18 Uhr)."""
    if not pacing.is_flush_window():
        return 0
    sent = 0
    for campaign in (
        config.CAMPAIGN_PARTNER,
        config.CAMPAIGN_REFERRAL,
        config.CAMPAIGN_BAUHERR,
    ):
        if campaign == config.CAMPAIGN_REFERRAL and not config.REFERRAL_ENABLED:
            continue
        if campaign == config.CAMPAIGN_BAUHERR and not config.BAUHERR_ENABLED:
            continue
        daily_limit, _ = _send_limits(campaign)
        remaining = daily_limit - storage.get_counter("sent", campaign)
        if remaining <= 0:
            continue
        n = _send_campaign_burst(campaign, remaining)
        sent += n
        if n:
            print(f"[outreach] ⏰ End-of-Day-Flush ({campaign}): +{n}", flush=True)
    return sent
