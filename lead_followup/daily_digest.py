"""Tägliches Fazit: welche Leads die 8-Uhr-Follow-up-Mail erhalten haben."""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

try:
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

from company_config import company_footer_text
from lead_followup import config, storage
from lead_followup.resend_sync import sync_scheduled_status

try:
    from mailer import email_configured, send_email
except ImportError:
    email_configured = lambda: False  # type: ignore
    send_email = None  # type: ignore

TZ = ZoneInfo("Europe/Berlin")
GOLD = "#b87333"
TEXT = "#1a1a1a"
MUTED = "#666666"
SUCCESS = "#15803d"
WARN = "#b45309"
ERROR = "#b91c1c"


def _today() -> date:
    return datetime.now(TZ).date()


def _date_label(d: date) -> str:
    weekdays = (
        "Montag", "Dienstag", "Mittwoch", "Donnerstag",
        "Freitag", "Samstag", "Sonntag",
    )
    months = (
        "", "Januar", "Februar", "März", "April", "Mai", "Juni",
        "Juli", "August", "September", "Oktober", "November", "Dezember",
    )
    return f"{weekdays[d.weekday()]}, {d.day}. {months[d.month]} {d.year}"


def _safe(s: str) -> str:
    return (
        str(s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _display_company(row) -> str:
    company = (row["company"] or "").strip()
    if company and company != "—":
        return company
    return (row["name"] or "").strip() or "—"


def _role_short(row) -> str:
    role = (row["role"] or "").strip()
    if role == "bauherr":
        return "Bauherr"
    if role == "unternehmen":
        return "Partner"
    return (row["role_label"] or role or "—")[:40]


def _status_label(status: str) -> tuple[str, str]:
    if status == "sent":
        return "Versendet", SUCCESS
    if status == "scheduled":
        return "Unterwegs", WARN
    if status == "failed":
        return "Fehler", ERROR
    return status, MUTED


def gather_digest_data(for_day: date | None = None) -> dict:
    day = for_day or _today()
    day_iso = day.isoformat()
    storage.init_db()
    sync_scheduled_status()
    rows = storage.followups_on_day(day_iso)

    companies = []
    sent_list = []
    sent = scheduled = failed = pending = 0
    for row in rows:
        st = row["status"]
        if st == "sent":
            sent += 1
        elif st == "scheduled":
            scheduled += 1
        elif st == "failed":
            failed += 1
        else:
            pending += 1
        label, _ = _status_label(st)
        entry = {
            "ref": row["ref"],
            "company": _display_company(row),
            "name": row["name"],
            "email": row["email"],
            "role": _role_short(row),
            "status": label,
            "status_raw": st,
            "time": (row["scheduled_for"] or "")[11:16],
        }
        companies.append(entry)
        if st == "sent":
            sent_list.append(entry)

    in_progress = scheduled + pending
    all_complete = len(rows) > 0 and in_progress == 0

    return {
        "date_label": _date_label(day),
        "date_iso": day_iso,
        "total": len(rows),
        "sent": sent,
        "scheduled": scheduled,
        "failed": failed,
        "pending": pending,
        "in_progress": in_progress,
        "all_complete": all_complete,
        "companies": companies,
        "sent_companies": sent_list,
        "followup_hour": config.FOLLOWUP_HOUR,
    }


def _earliest_digest_time(for_day: date | None = None) -> datetime:
    """Erst nach Follow-up-Zeit + kurzer Puffer (z. B. 8:15)."""
    day = for_day or _today()
    base = datetime(
        day.year, day.month, day.day,
        config.FOLLOWUP_HOUR, config.FOLLOWUP_MINUTE, 0,
        tzinfo=TZ,
    )
    return base + timedelta(minutes=config.DIGEST_GRACE_MINUTES)


def _fallback_digest_time(for_day: date | None = None) -> datetime:
    day = for_day or _today()
    return datetime(
        day.year, day.month, day.day,
        config.DIGEST_FALLBACK_HOUR, 0, 0,
        tzinfo=TZ,
    )


def should_send_digest() -> bool:
    """Fazit senden, wenn alle Follow-ups fertig — spätestens zum Fallback (10:00)."""
    storage.init_db()
    now = datetime.now(TZ)
    day_iso = _today().isoformat()

    if storage.digest_was_sent(day_iso):
        return False
    if now < _earliest_digest_time():
        return False

    data = gather_digest_data()
    if data["total"] == 0:
        return False

    if data["all_complete"]:
        return True

    return now >= _fallback_digest_time()


def build_digest_email(data: dict) -> tuple[str, str, str]:
    total = data["total"]
    sent = data["sent"]
    sent_list = data["sent_companies"]

    if data["all_complete"] and sent == total:
        subject = (
            f"Follow-ups abgeschlossen · {data['date_label']} · "
            f"{sent} Firma{'en' if sent != 1 else ''} erhalten"
        )
    else:
        subject = (
            f"Lead-Follow-up Fazit · {data['date_label']} · {sent} von {total} versendet"
            if total
            else f"Lead-Follow-up Fazit · {data['date_label']} · keine Versände"
        )

    lines = [
        f"Lead-Follow-up — Abschlussbericht",
        f"{data['date_label']}",
        "",
    ]

    if sent_list:
        lines.append("DIESE FIRMEN HABEN DIE FOLLOW-UP-NACHRICHT ERHALTEN:")
        lines.append("=" * 50)
        for i, c in enumerate(sent_list, 1):
            lines.append(
                f"{i}. {c['company']} ({c['name']}) — {c['email']} — {c['role']} — {c['ref']}"
            )
        lines.append("")

    lines.extend([
        f"Versand geplant um:     {data['followup_hour']:02d}:00 Uhr (Europe/Berlin)",
        f"Gesamt geplant:         {total}",
        f"Erfolgreich versendet:  {sent}",
        f"Noch ausstehend:        {data['in_progress']}",
        f"Fehler:                 {data['failed']}",
        "",
    ])

    if data["companies"] and not sent_list:
        lines.append("── Alle geplanten Leads ──")
        for i, c in enumerate(data["companies"], 1):
            lines.append(
                f"{i}. {c['company']} | {c['name']} | {c['email']} | "
                f"{c['role']} | {c['status']} | {c['ref']}"
            )
    elif data["companies"] and (data["failed"] or data["in_progress"]):
        others = [c for c in data["companies"] if c["status_raw"] != "sent"]
        if others:
            lines.append("── Noch nicht / fehlgeschlagen ──")
            for i, c in enumerate(others, 1):
                lines.append(
                    f"{i}. {c['company']} | {c['email']} | {c['status']} | {c['ref']}"
                )

    lines.extend(["", company_footer_text()])
    text_body = "\n".join(lines)

    if sent_list:
        sent_rows = []
        for i, c in enumerate(sent_list, 1):
            sent_rows.append(
                f"""<tr>
  <td style="padding:12px 14px;border-bottom:1px solid #eee;font-size:13px;color:{MUTED}">{i}</td>
  <td style="padding:12px 14px;border-bottom:1px solid #eee;font-size:14px;color:{TEXT}"><strong>{_safe(c['company'])}</strong></td>
  <td style="padding:12px 14px;border-bottom:1px solid #eee;font-size:12px;color:{MUTED}">{_safe(c['name'])}</td>
  <td style="padding:12px 14px;border-bottom:1px solid #eee;font-size:12px;color:{GOLD}">{_safe(c['email'])}</td>
  <td style="padding:12px 14px;border-bottom:1px solid #eee;font-size:12px;color:{MUTED}">{_safe(c['role'])}</td>
  <td style="padding:12px 14px;border-bottom:1px solid #eee;font-size:11px;color:#999">{_safe(c['ref'])}</td>
</tr>"""
            )
        sent_table = f"""
<p style="margin:0 0 12px;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:{SUCCESS};font-weight:600">
  Diese Firmen haben die Follow-up-Nachricht erhalten
</p>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border:1px solid #d1e7dd;margin-bottom:24px">
<tr style="background:#ecfdf5">
  <th style="padding:10px 14px;text-align:left;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:{SUCCESS}">#</th>
  <th style="padding:10px 14px;text-align:left;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:{SUCCESS}">Firma</th>
  <th style="padding:10px 14px;text-align:left;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:{SUCCESS}">Ansprechpartner</th>
  <th style="padding:10px 14px;text-align:left;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:{SUCCESS}">E-Mail</th>
  <th style="padding:10px 14px;text-align:left;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:{SUCCESS}">Typ</th>
  <th style="padding:10px 14px;text-align:left;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:{SUCCESS}">Ref</th>
</tr>
{"".join(sent_rows)}
</table>"""
    else:
        sent_table = (
            f'<p style="margin:0 0 20px;font-size:14px;color:{MUTED}">'
            f"Noch keine bestätigten Versände für heute.</p>"
        )

    if not data["companies"]:
        table_html = sent_table
    else:
        rows_html = []
        for i, c in enumerate(data["companies"], 1):
            if c["status_raw"] == "sent":
                continue
            _, color = _status_label(c["status_raw"])
            rows_html.append(
                f"""<tr>
  <td style="padding:10px 12px;border-bottom:1px solid #eee;font-size:13px;color:{MUTED}">{i}</td>
  <td style="padding:10px 12px;border-bottom:1px solid #eee;font-size:13px;color:{TEXT}"><strong>{_safe(c['company'])}</strong></td>
  <td style="padding:10px 12px;border-bottom:1px solid #eee;font-size:12px;color:{GOLD}">{_safe(c['email'])}</td>
  <td style="padding:10px 12px;border-bottom:1px solid #eee;font-size:12px;color:{color};font-weight:600">{_safe(c['status'])}</td>
</tr>"""
            )
        other_table = ""
        if rows_html:
            other_table = f"""
<p style="margin:24px 0 8px;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:{WARN}">Ausstehend / Fehler</p>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border:1px solid #ebebeb">
<tr style="background:#f7f7f7">
  <th style="padding:10px 12px;text-align:left;font-size:10px;color:{GOLD}">#</th>
  <th style="padding:10px 12px;text-align:left;font-size:10px;color:{GOLD}">Firma</th>
  <th style="padding:10px 12px;text-align:left;font-size:10px;color:{GOLD}">E-Mail</th>
  <th style="padding:10px 12px;text-align:left;font-size:10px;color:{GOLD}">Status</th>
</tr>
{"".join(rows_html)}
</table>"""
        table_html = sent_table + other_table

    headline = (
        "Alle Follow-ups abgeschlossen"
        if data["all_complete"]
        else "Lead-Follow-up Status"
    )

    inner = f"""<tr><td style="padding:40px 40px 24px;border-bottom:1px solid #e8e8e8">
  <p style="margin:0 0 16px;font-family:Arial,sans-serif;font-size:11px;letter-spacing:0.35em;text-transform:uppercase;color:{GOLD}">Kaplan Solutions</p>
  <p style="margin:0;font-family:Georgia,serif;font-size:26px;color:{TEXT}">{headline}</p>
  <p style="margin:8px 0 0;font-family:Arial,sans-serif;font-size:14px;color:{MUTED}">{_safe(data['date_label'])} · Versand um {data['followup_hour']:02d}:00 Uhr</p>
</td></tr>
<tr><td style="padding:32px 40px;font-family:Arial,sans-serif;color:{MUTED}">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr>
    <td width="33%" style="padding:8px;text-align:center;background:#f7f7f7;border:1px solid #ebebeb">
      <p style="margin:0;font-size:28px;font-weight:700;color:{GOLD}">{total}</p>
      <p style="margin:4px 0 0;font-size:10px;letter-spacing:0.12em;text-transform:uppercase;color:{MUTED}">Geplant</p>
    </td>
    <td width="33%" style="padding:8px;text-align:center;background:#ecfdf5;border:1px solid #d1e7dd">
      <p style="margin:0;font-size:28px;font-weight:700;color:{SUCCESS}">{sent}</p>
      <p style="margin:4px 0 0;font-size:10px;letter-spacing:0.12em;text-transform:uppercase;color:{MUTED}">Erhalten</p>
    </td>
    <td width="33%" style="padding:8px;text-align:center;background:#f7f7f7;border:1px solid #ebebeb">
      <p style="margin:0;font-size:28px;font-weight:700;color:{ERROR}">{data['failed']}</p>
      <p style="margin:4px 0 0;font-size:10px;letter-spacing:0.12em;text-transform:uppercase;color:{MUTED}">Fehler</p>
    </td>
  </tr></table>
  <div style="margin-top:28px">{table_html}</div>
</td></tr>
<tr><td style="padding:0 40px 40px;font-size:12px;color:#aaa;border-top:1px solid #e8e8e8">
  <p style="margin:24px 0 0">{_safe(company_footer_text()).replace(chr(10), '<br>')}</p>
</td></tr>"""

    html_body = f"""<!DOCTYPE html><html lang="de"><head><meta charset="utf-8"></head><body style="margin:0;background:#f0f0f0">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f0f0f0;padding:32px 16px">
<tr><td align="center"><table role="presentation" width="600" style="max-width:600px;background:#fff">{inner}</table></td></tr>
</table></body></html>"""

    return subject, text_body, html_body


def send_daily_digest(for_day: date | None = None, force: bool = False) -> bool:
    day = for_day or _today()
    day_iso = day.isoformat()
    storage.init_db()

    if not force and storage.digest_was_sent(day_iso):
        return False
    digest_to = (
        os.getenv("LEAD_DIGEST_EMAIL", "").strip()
        or os.getenv("OUTREACH_REPORT_EMAIL", "").strip()
        or os.getenv("ADMIN_EMAIL", "").strip()
    )
    if not email_configured() or not digest_to:
        print("[lead_digest] E-Mail nicht konfiguriert.", flush=True)
        return False

    data = gather_digest_data(day)
    subject, text_body, html_body = build_digest_email(data)

    try:
        send_email(digest_to, subject, text_body, html_body)  # type: ignore
        storage.mark_digest_sent(day_iso)
        print(
            f"[lead_digest] Fazit gesendet an {digest_to} "
            f"({data['sent']}/{data['total']} versendet)",
            flush=True,
        )
        return True
    except Exception as exc:
        print(f"[lead_digest] Fehlgeschlagen: {exc}", flush=True)
        return False


def maybe_send_digest() -> bool:
    if not should_send_digest():
        return False
    return send_daily_digest()
