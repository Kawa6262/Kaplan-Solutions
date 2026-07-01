"""Mittags-Update 13:00 Uhr — Fortschritt bis halber Tag."""

from __future__ import annotations

import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

from outreach import config
from outreach import schedule
from outreach import storage

try:
    from mailer import email_configured, send_email
except ImportError:
    email_configured = lambda: False  # type: ignore
    send_email = None  # type: ignore

REPORT_EMAIL = os.getenv(
    "OUTREACH_MIDDAY_REPORT_EMAIL",
    os.getenv("OUTREACH_MORNING_REPORT_EMAIL", os.getenv("ADMIN_EMAIL", "")),
).strip()
MIDDAY_HOUR = int(os.getenv("OUTREACH_MIDDAY_REPORT_HOUR", "13"))


def _today_berlin() -> date:
    return datetime.now(ZoneInfo("Europe/Berlin")).date()


def _date_label(d: date) -> str:
    weekdays = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")
    months = (
        "", "Januar", "Februar", "März", "April", "Mai", "Juni",
        "Juli", "August", "September", "Oktober", "November", "Dezember",
    )
    return f"{weekdays[d.weekday()]}, {d.day}. {months[d.month]} {d.year}"


def _total_limit() -> int:
    total = config.DAILY_SEND_LIMIT
    if config.REFERRAL_ENABLED:
        total += config.REFERRAL_DAILY_SEND_LIMIT
    if config.BAUHERR_ENABLED:
        total += config.BAUHERR_DAILY_SEND_LIMIT
    return total


def gather_midday_data() -> dict:
    today = _today_berlin()
    c = storage.get_daily_counters(today.isoformat())
    summary = storage.stats_summary()
    ss = storage.sheet_sync_stats()

    partner = c.get("sent", 0)
    referral = c.get("referral_sent", 0)
    bauherr = c.get("bauherr_sent", 0)
    total = partner + referral + bauherr
    limit = _total_limit()

    partner_rem = max(0, config.DAILY_SEND_LIMIT - partner)
    referral_rem = max(0, config.REFERRAL_DAILY_SEND_LIMIT - referral) if config.REFERRAL_ENABLED else 0
    bauherr_rem = max(0, config.BAUHERR_DAILY_SEND_LIMIT - bauherr) if config.BAUHERR_ENABLED else 0

    return {
        "date_label": _date_label(today),
        "window": f"{config.SEND_HOUR_START}:00–{config.SEND_HOUR_END}:00 Uhr",
        "partner_sent": partner,
        "referral_sent": referral,
        "bauherr_sent": bauherr,
        "total_sent": total,
        "total_limit": limit,
        "total_remaining": max(0, limit - total),
        "partner_limit": config.DAILY_SEND_LIMIT,
        "referral_limit": config.REFERRAL_DAILY_SEND_LIMIT if config.REFERRAL_ENABLED else 0,
        "bauherr_limit": config.BAUHERR_DAILY_SEND_LIMIT if config.BAUHERR_ENABLED else 0,
        "partner_remaining": partner_rem,
        "referral_remaining": referral_rem,
        "bauherr_remaining": bauherr_rem,
        "failed_today": storage.prospects_failed_on_day(today.isoformat()),
        "queued": summary["queued"],
        "sheet_pending": ss["pending"],
        "pct": min(100, int(total / max(1, limit) * 100)),
    }


def build_midday_email(data: dict) -> tuple[str, str, str]:
    failed_n = len(data["failed_today"])
    subject = (
        f"📊 Outreach Mittags-Update · {data['total_sent']}/{data['total_limit']} "
        f"({data['pct']}%) · {data['date_label']}"
    )
    text = f"""Mittags-Update — {data['date_label']}

FORTSCHRITT HEUTE ({data['window']})
• Partner:   {data['partner_sent']} / {data['partner_limit']}  (noch {data['partner_remaining']})
• Referral:  {data['referral_sent']} / {data['referral_limit']}  (noch {data['referral_remaining']})
• Bauherr:   {data['bauherr_sent']} / {data['bauherr_limit']}  (noch {data['bauherr_remaining']})
• GESAMT:    {data['total_sent']} / {data['total_limit']}  ({data['pct']}%)

Nachmittag: bis {data['total_remaining']} weitere Mails möglich
Warteschlange: {data['queued']} · Sheet ausstehend: {data['sheet_pending']}
Fehler heute: {failed_n}

Abends erhältst du das vollständige Tagesfazit (~18:00).

Kaplan Solutions · Outreach-Daemon
"""
    html = f"""<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#1a1a1a;line-height:1.6;max-width:560px">
<h2 style="color:#0b3d2e;margin:0 0 8px">📊 Mittags-Update — {data['date_label']}</h2>
<p>Stand 13:00 · Versand läuft bis <strong>{data['window']}</strong></p>
<div style="background:#e8f5e9;border-radius:8px;padding:16px;margin:16px 0;text-align:center">
  <p style="margin:0;font-size:32px;font-weight:700;color:#0b3d2e">{data['total_sent']} / {data['total_limit']}</p>
  <p style="margin:4px 0 0;color:#666">{data['pct']}% des Tageslimits · noch {data['total_remaining']} bis Abend</p>
</div>
<table style="width:100%;border-collapse:collapse;margin:16px 0">
<tr style="background:#f0f0f0"><th style="padding:8px;text-align:left">Kampagne</th><th style="padding:8px;text-align:right">Heute</th><th style="padding:8px;text-align:right">Offen</th></tr>
<tr><td style="padding:8px;border-bottom:1px solid #eee">Partner</td><td style="padding:8px;text-align:right;border-bottom:1px solid #eee"><strong>{data['partner_sent']}</strong> / {data['partner_limit']}</td><td style="padding:8px;text-align:right;border-bottom:1px solid #eee">{data['partner_remaining']}</td></tr>
<tr><td style="padding:8px;border-bottom:1px solid #eee">Referral</td><td style="padding:8px;text-align:right;border-bottom:1px solid #eee"><strong>{data['referral_sent']}</strong> / {data['referral_limit']}</td><td style="padding:8px;text-align:right;border-bottom:1px solid #eee">{data['referral_remaining']}</td></tr>
<tr><td style="padding:8px;border-bottom:1px solid #eee">Bauherr</td><td style="padding:8px;text-align:right;border-bottom:1px solid #eee"><strong>{data['bauherr_sent']}</strong> / {data['bauherr_limit']}</td><td style="padding:8px;text-align:right;border-bottom:1px solid #eee">{data['bauherr_remaining']}</td></tr>
</table>
<p style="font-size:13px;color:#666">Queue: {data['queued']} · Sheet: {data['sheet_pending']} ausstehend · Fehler: {failed_n}</p>
</body></html>"""
    return subject, text, html


def send_midday_report(force: bool = False) -> bool:
    day_iso = _today_berlin().isoformat()
    if not force and storage.midday_report_was_sent(day_iso):
        return False
    if not email_configured() or not REPORT_EMAIL:
        print("[outreach] Mittags-Update: E-Mail nicht konfiguriert.", flush=True)
        return False
    data = gather_midday_data()
    subject, text, html = build_midday_email(data)
    try:
        send_email(REPORT_EMAIL, subject, text, html)  # type: ignore
        storage.mark_midday_report_sent(day_iso)
        print(
            f"[outreach] 📊 Mittags-Update → {REPORT_EMAIL} "
            f"({data['total_sent']}/{data['total_limit']})",
            flush=True,
        )
        return True
    except Exception as exc:
        print(f"[outreach] Mittags-Update fehlgeschlagen: {exc}", flush=True)
        return False


def maybe_send_midday_report() -> bool:
    day_iso = _today_berlin().isoformat()
    if not schedule.should_send_at_hour(MIDDAY_HOUR, storage.midday_report_was_sent(day_iso)):
        return False
    return send_midday_report()
