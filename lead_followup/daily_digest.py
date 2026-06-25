"""Tägliches Fazit: welche Leads die 8-Uhr-Follow-up-Mail erhalten haben."""

from __future__ import annotations

import os
from datetime import date, datetime
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
        companies.append(
            {
                "ref": row["ref"],
                "company": _display_company(row),
                "name": row["name"],
                "email": row["email"],
                "role": _role_short(row),
                "status": label,
                "status_raw": st,
                "time": (row["scheduled_for"] or "")[11:16],
            }
        )

    return {
        "date_label": _date_label(day),
        "date_iso": day_iso,
        "total": len(rows),
        "sent": sent,
        "scheduled": scheduled,
        "failed": failed,
        "pending": pending,
        "companies": companies,
        "followup_hour": config.FOLLOWUP_HOUR,
    }


def should_send_digest() -> bool:
    now = datetime.now(TZ)
    if (now.hour, now.minute) < (config.DIGEST_HOUR, config.DIGEST_MINUTE):
        return False
    return not storage.digest_was_sent(_today().isoformat())


def build_digest_email(data: dict) -> tuple[str, str, str]:
    total = data["total"]
    sent = data["sent"]
    subject = (
        f"Lead-Follow-up Fazit · {data['date_label']} · {sent} von {total} versendet"
        if total
        else f"Lead-Follow-up Fazit · {data['date_label']} · keine Versände"
    )

    lines = [
        f"Lead-Follow-up Fazit — {data['date_label']}",
        "",
        f"Versandfenster heute: {data['followup_hour']:02d}:00 Uhr (Europe/Berlin)",
        "",
        f"Gesamt geplant heute:  {total}",
        f"Erfolgreich versendet: {sent}",
        f"Noch unterwegs:        {data['scheduled']}",
        f"Ausstehend:            {data['pending']}",
        f"Fehler:                {data['failed']}",
        "",
    ]

    if data["companies"]:
        lines.append("── Firmen / Leads ──")
        for i, c in enumerate(data["companies"], 1):
            lines.append(
                f"{i}. {c['company']} | {c['name']} | {c['email']} | "
                f"{c['role']} | {c['status']} | {c['ref']}"
            )
    else:
        lines.append("Heute wurden keine Follow-up-Mails geplant.")

    lines.extend(["", company_footer_text()])
    text_body = "\n".join(lines)

    if not data["companies"]:
        table_html = (
            f'<p style="margin:0;font-family:Arial,sans-serif;font-size:14px;color:{MUTED}">'
            f"Heute wurden keine Follow-up-Mails für {data['followup_hour']:02d}:00 Uhr geplant.</p>"
        )
    else:
        rows_html = []
        for i, c in enumerate(data["companies"], 1):
            _, color = _status_label(c["status_raw"])
            rows_html.append(
                f"""<tr>
  <td style="padding:10px 12px;border-bottom:1px solid #eee;font-size:13px;color:{MUTED}">{i}</td>
  <td style="padding:10px 12px;border-bottom:1px solid #eee;font-size:13px;color:{TEXT}"><strong>{_safe(c['company'])}</strong><br><span style="color:{MUTED};font-size:12px">{_safe(c['name'])}</span></td>
  <td style="padding:10px 12px;border-bottom:1px solid #eee;font-size:12px;color:{GOLD}">{_safe(c['email'])}</td>
  <td style="padding:10px 12px;border-bottom:1px solid #eee;font-size:12px;color:{MUTED}">{_safe(c['role'])}</td>
  <td style="padding:10px 12px;border-bottom:1px solid #eee;font-size:12px;color:{color};font-weight:600">{_safe(c['status'])}</td>
  <td style="padding:10px 12px;border-bottom:1px solid #eee;font-size:11px;color:#999">{_safe(c['ref'])}</td>
</tr>"""
            )
        table_html = f"""
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border:1px solid #ebebeb;margin-top:12px">
<tr style="background:#f7f7f7">
  <th style="padding:10px 12px;text-align:left;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:{GOLD}">#</th>
  <th style="padding:10px 12px;text-align:left;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:{GOLD}">Firma / Name</th>
  <th style="padding:10px 12px;text-align:left;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:{GOLD}">E-Mail</th>
  <th style="padding:10px 12px;text-align:left;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:{GOLD}">Typ</th>
  <th style="padding:10px 12px;text-align:left;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:{GOLD}">Status</th>
  <th style="padding:10px 12px;text-align:left;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:{GOLD}">Ref</th>
</tr>
{"".join(rows_html)}
</table>"""

    inner = f"""<tr><td style="padding:40px 40px 24px;border-bottom:1px solid #e8e8e8">
  <p style="margin:0 0 16px;font-family:Arial,sans-serif;font-size:11px;letter-spacing:0.35em;text-transform:uppercase;color:{GOLD}">Kaplan Solutions</p>
  <p style="margin:0;font-family:Georgia,serif;font-size:26px;color:{TEXT}">Lead-Follow-up Tagesfazit</p>
  <p style="margin:8px 0 0;font-family:Arial,sans-serif;font-size:14px;color:{MUTED}">{_safe(data['date_label'])} · Versand um {data['followup_hour']:02d}:00 Uhr</p>
</td></tr>
<tr><td style="padding:32px 40px;font-family:Arial,sans-serif;color:{MUTED}">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr>
    <td width="25%" style="padding:8px;text-align:center;background:#f7f7f7;border:1px solid #ebebeb">
      <p style="margin:0;font-size:28px;font-weight:700;color:{GOLD}">{total}</p>
      <p style="margin:4px 0 0;font-size:10px;letter-spacing:0.12em;text-transform:uppercase;color:{MUTED}">Geplant</p>
    </td>
    <td width="25%" style="padding:8px;text-align:center;background:#f7f7f7;border:1px solid #ebebeb">
      <p style="margin:0;font-size:28px;font-weight:700;color:{SUCCESS}">{sent}</p>
      <p style="margin:4px 0 0;font-size:10px;letter-spacing:0.12em;text-transform:uppercase;color:{MUTED}">Versendet</p>
    </td>
    <td width="25%" style="padding:8px;text-align:center;background:#f7f7f7;border:1px solid #ebebeb">
      <p style="margin:0;font-size:28px;font-weight:700;color:{WARN}">{data['scheduled']}</p>
      <p style="margin:4px 0 0;font-size:10px;letter-spacing:0.12em;text-transform:uppercase;color:{MUTED}">Unterwegs</p>
    </td>
    <td width="25%" style="padding:8px;text-align:center;background:#f7f7f7;border:1px solid #ebebeb">
      <p style="margin:0;font-size:28px;font-weight:700;color:{ERROR}">{data['failed']}</p>
      <p style="margin:4px 0 0;font-size:10px;letter-spacing:0.12em;text-transform:uppercase;color:{MUTED}">Fehler</p>
    </td>
  </tr></table>
  <p style="margin:24px 0 8px;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:{GOLD}">Empfänger heute</p>
  {table_html}
</td></tr>
<tr><td style="padding:0 40px 40px;font-size:12px;color:#aaa;border-top:1px solid #e8e8e8">
  <p style="margin:24px 0 0">{_safe(company_footer_text()).replace(chr(10), '<br>')}</p>
</td></tr>"""

    html_body = f"""<!DOCTYPE html><html lang="de"><body style="margin:0;background:#f0f0f0">
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
