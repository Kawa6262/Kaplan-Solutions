"""Tägliches Outreach-Fazit per E-Mail an den Admin."""

from __future__ import annotations

import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

from outreach import config
from outreach import storage
from outreach.report_template import build_daily_report

try:
    from mailer import email_configured, send_email
except ImportError:
    email_configured = lambda: False  # type: ignore
    send_email = None  # type: ignore

REPORT_EMAIL = os.getenv("OUTREACH_REPORT_EMAIL", os.getenv("ADMIN_EMAIL", "")).strip()
REPORT_HOUR = int(os.getenv("OUTREACH_REPORT_HOUR", "18"))
REPORT_FINAL_HOUR = int(os.getenv("OUTREACH_REPORT_FINAL_HOUR", "20"))


def _today_berlin() -> date:
    return datetime.now(ZoneInfo("Europe/Berlin")).date()


def _date_label(d: date) -> str:
    weekdays = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")
    months = (
        "", "Januar", "Februar", "März", "April", "Mai", "Juni",
        "Juli", "August", "September", "Oktober", "November", "Dezember",
    )
    return f"{weekdays[d.weekday()]}, {d.day}. {months[d.month]} {d.year}"


def _search_progress_label(campaign: str = "partner") -> str:
    trade_idx, city_idx, token = storage.get_search_cursor(campaign)
    if campaign == "referral":
        trades = config.REFERRAL_TRADE_QUERIES
        prefix = "Referral"
    else:
        trades = config.TRADE_QUERIES
        prefix = "Partner"
    trade = trades[trade_idx % len(trades)]
    city = config.GERMAN_CITIES[city_idx % len(config.GERMAN_CITIES)]
    page = " (weitere Seite)" if token else ""
    return f"{prefix}: {trade} · {city} · {trade_idx + 1}/{len(trades)}{page}"


def gather_report_data(for_day: date | None = None) -> dict:
    day = for_day or _today_berlin()
    day_iso = day.isoformat()
    summary = storage.stats_summary()
    counters = storage.get_daily_counters(day_iso)

    companies_sent = storage.prospects_sent_on_day(day_iso)
    companies_failed = storage.prospects_failed_on_day(day_iso)

    return {
        "date_label": _date_label(day),
        "date_iso": day_iso,
        "sent_today": counters.get("sent", 0),
        "discovered_today": counters.get("discovered", 0),
        "enriched_today": counters.get("enriched", 0),
        "failed_today": len(companies_failed),
        "skipped_today": storage.skipped_on_day(day_iso),
        "sent_limit": config.DAILY_SEND_LIMIT,
        "discover_limit": config.DAILY_DISCOVER_LIMIT,
        "queued": summary["queued"],
        "sent_all_time": summary["sent_all_time"],
        "total_prospects": summary["total"],
        "unsubscribes": storage.unsubscribe_count(),
        "companies_sent": companies_sent,
        "companies_failed": companies_failed,
        "by_city": storage.sent_breakdown_by_city(day_iso),
        "by_trade": storage.sent_breakdown_by_trade(day_iso),
        "search_progress": _search_progress_label("partner"),
        "referral_search_progress": _search_progress_label("referral"),
        "referral_sent_today": counters.get("referral_sent", 0),
        "referral_discovered_today": counters.get("referral_discovered", 0),
        "referral_sent_limit": config.REFERRAL_DAILY_SEND_LIMIT,
        "referral_enabled": config.REFERRAL_ENABLED,
    }


def should_send_report() -> bool:
    now = datetime.now(ZoneInfo("Europe/Berlin"))
    day_iso = _today_berlin().isoformat()
    if storage.report_was_sent(day_iso):
        return False
    if now.hour < REPORT_HOUR:
        return False

    counters = storage.get_daily_counters(day_iso)
    sent_today = counters.get("sent", 0)

    # Tageslimit erreicht → Fazit ab REPORT_HOUR
    if sent_today >= config.DAILY_SEND_LIMIT:
        return True

    # Sonst warten bis Sendefenster vorbei oder Final-Stunde (Nachholversand)
    if now.hour >= REPORT_FINAL_HOUR:
        return True

    # Noch im Sendefenster und Limit nicht voll → weiter versenden, kein Fazit
    if now.hour < config.SEND_HOUR_END:
        return False

    # 18–20 Uhr: Fazit erst wenn wirklich nichts mehr geht (keine Queue)
    if storage.stats_summary()["queued"] == 0:
        return True

    return False


def send_daily_report(for_day: date | None = None, force: bool = False) -> bool:
    day = for_day or _today_berlin()
    day_iso = day.isoformat()

    if not force and storage.report_was_sent(day_iso):
        return False
    if not email_configured() or not REPORT_EMAIL:
        print("[outreach] Tagesfazit: E-Mail nicht konfiguriert.", flush=True)
        return False

    data = gather_report_data(day)
    subject, text_body, html_body = build_daily_report(data)

    try:
        send_email(REPORT_EMAIL, subject, text_body, html_body)  # type: ignore
        storage.mark_report_sent(day_iso)
        print(
            f"[outreach] Tagesfazit gesendet an {REPORT_EMAIL} "
            f"({data['sent_today']} Kontakte)",
            flush=True,
        )
        return True
    except Exception as exc:
        print(f"[outreach] Tagesfazit fehlgeschlagen: {exc}", flush=True)
        return False


def maybe_send_report() -> bool:
    """Im Daemon aufrufen — sendet einmal täglich nach REPORT_HOUR."""
    if not should_send_report():
        return False
    return send_daily_report()
