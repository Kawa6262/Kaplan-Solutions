"""Morgen-Update per E-Mail — Tagesstart 8:00 Uhr (Outreach + Queue + Matching)."""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from outreach import config
from outreach import schedule
from outreach import storage

try:
    from mailer import email_configured, send_email
except ImportError:
    email_configured = lambda: False  # type: ignore
    send_email = None  # type: ignore

REPORT_EMAIL = os.getenv("OUTREACH_MORNING_REPORT_EMAIL", os.getenv("ADMIN_EMAIL", "")).strip()
MORNING_HOUR = int(os.getenv("OUTREACH_MORNING_REPORT_HOUR", "8"))


def _today_berlin() -> date:
    return datetime.now(ZoneInfo("Europe/Berlin")).date()


def _date_label(d: date) -> str:
    weekdays = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")
    months = (
        "", "Januar", "Februar", "März", "April", "Mai", "Juni",
        "Juli", "August", "September", "Oktober", "November", "Dezember",
    )
    return f"{weekdays[d.weekday()]}, {d.day}. {months[d.month]} {d.year}"


def morning_report_was_sent(day: str) -> bool:
    return storage.get_daily_counters(day).get("morning_report_sent", 0) > 0


def mark_morning_report_sent(day: str) -> None:
    storage.mark_morning_report_sent(day)


def gather_morning_data() -> dict:
    today = _today_berlin()
    yesterday = today - timedelta(days=1)
    summary = storage.stats_summary()
    today_c = storage.get_daily_counters(today.isoformat())
    y_c = storage.get_daily_counters(yesterday.isoformat())
    ss = storage.sheet_sync_stats()

    partner_y = y_c.get("sent", 0)
    referral_y = y_c.get("referral_sent", 0)
    bauherr_y = y_c.get("bauherr_sent", 0)

    return {
        "date_label": _date_label(today),
        "window": f"{config.SEND_HOUR_START}:00–{config.SEND_HOUR_END}:00 Uhr",
        "partner_sent_yesterday": partner_y,
        "referral_sent_yesterday": referral_y,
        "bauherr_sent_yesterday": bauherr_y,
        "total_sent_yesterday": partner_y + referral_y + bauherr_y,
        "partner_limit": config.DAILY_SEND_LIMIT,
        "referral_limit": config.REFERRAL_DAILY_SEND_LIMIT if config.REFERRAL_ENABLED else 0,
        "bauherr_limit": config.BAUHERR_DAILY_SEND_LIMIT if config.BAUHERR_ENABLED else 0,
        "partner_queued": summary["partner_queued"],
        "referral_queued": summary.get("referral_queued", 0),
        "bauherr_queued": summary.get("bauherr_queued", 0),
        "sent_all_time": summary["sent_all_time"],
        "sheet_pending": ss["pending"],
        "sheet_synced": ss["synced"],
        "briefing_hour": os.getenv("MATCH_BRIEFING_HOUR", "10"),
    }


def build_morning_email(data: dict) -> tuple[str, str, str]:
    subject = f"☀ Kaplan Outreach startet · {data['date_label']}"
    text = f"""Guten Morgen,

Outreach läuft heute automatisch ({data['window']}).

GESTERN KONTAKTIERT
• Partner-Firmen:    {data['partner_sent_yesterday']} E-Mails
• Referral (Makler/Architekten): {data['referral_sent_yesterday']} E-Mails
• Bauherr / Projekt: {data['bauherr_sent_yesterday']} E-Mails
• Gesamt:            {data['total_sent_yesterday']} E-Mails

HEUTE GEPLANT (Limits)
• Partner:  bis {data['partner_limit']}/Tag · Warteschlange: {data['partner_queued']}
• Referral: bis {data['referral_limit']}/Tag · Warteschlange: {data['referral_queued']}
• Bauherr:  bis {data['bauherr_limit']}/Tag · Warteschlange: {data['bauherr_queued']}

Portfolio-Sync: {data['sheet_synced']} im Sheet · {data['sheet_pending']} ausstehend
Magic Match Briefing: ca. {data['briefing_hour']}:00 Uhr
Gesamt versendet (all time): {data['sent_all_time']}

Du musst nichts tun — alles läuft automatisch.
Mittags-Update: ca. 13:00 Uhr · Abends Tagesfazit ~18:00.

Kaplan Solutions · Outreach-Daemon
"""
    html = f"""<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#1a1a1a;line-height:1.6;max-width:560px">
<h2 style="color:#0b3d2e;margin:0 0 8px">☀ Outreach startet — {data['date_label']}</h2>
<p>Automatischer Versand <strong>{data['window']}</strong> · Du musst nichts tun.</p>
<table style="width:100%;border-collapse:collapse;margin:16px 0">
<tr style="background:#f0f0f0"><th style="padding:8px;text-align:left">Gestern kontaktiert</th><th style="padding:8px;text-align:right">Anzahl</th></tr>
<tr><td style="padding:8px;border-bottom:1px solid #eee">Partner-Firmen</td><td style="padding:8px;text-align:right;border-bottom:1px solid #eee"><strong>{data['partner_sent_yesterday']}</strong></td></tr>
<tr><td style="padding:8px;border-bottom:1px solid #eee">Referral (Makler, Architekten…)</td><td style="padding:8px;text-align:right;border-bottom:1px solid #eee"><strong>{data['referral_sent_yesterday']}</strong></td></tr>
<tr><td style="padding:8px;border-bottom:1px solid #eee">Bauherr / Projektentwickler</td><td style="padding:8px;text-align:right;border-bottom:1px solid #eee"><strong>{data['bauherr_sent_yesterday']}</strong></td></tr>
<tr style="background:#e8f5e9"><td style="padding:8px"><strong>Gesamt</strong></td><td style="padding:8px;text-align:right"><strong>{data['total_sent_yesterday']}</strong></td></tr>
</table>
<p><strong>Heute:</strong> Partner {data['partner_queued']} in Queue (max {data['partner_limit']}) · Referral {data['referral_queued']} (max {data['referral_limit']}) · Bauherr {data['bauherr_queued']} (max {data['bauherr_limit']})</p>
<p style="font-size:13px;color:#666">Sheet: {data['sheet_synced']} sync · {data['sheet_pending']} ausstehend · Magic Match Briefing ~{data['briefing_hour']}:00 · Mittags-Update ~13:00</p>
</body></html>"""
    return subject, text, html


def send_morning_report(force: bool = False) -> bool:
    day_iso = _today_berlin().isoformat()
    if not force and morning_report_was_sent(day_iso):
        return False
    if not email_configured() or not REPORT_EMAIL:
        print("[outreach] Morgen-Report: E-Mail nicht konfiguriert.", flush=True)
        return False
    data = gather_morning_data()
    subject, text, html = build_morning_email(data)
    try:
        send_email(REPORT_EMAIL, subject, text, html)  # type: ignore
        mark_morning_report_sent(day_iso)
        print(f"[outreach] ☀ Morgen-Report → {REPORT_EMAIL}", flush=True)
        return True
    except Exception as exc:
        print(f"[outreach] Morgen-Report fehlgeschlagen: {exc}", flush=True)
        return False


def maybe_send_morning_report() -> bool:
    day_iso = _today_berlin().isoformat()
    if not schedule.should_send_at_hour(MORNING_HOUR, morning_report_was_sent(day_iso)):
        return False
    return send_morning_report()
