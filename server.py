#!/usr/bin/env python3
"""Kaplan Solutions — Website + Kontaktformular per E-Mail."""

import base64
import json
import os
import re
import smtplib
import ssl
import subprocess
import urllib.error
import urllib.request
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from flask import Flask, abort, jsonify, render_template, request, send_from_directory

from company_config import COMPANY, company_footer_text

BASE_DIR = Path(__file__).parent
INBOX_DIR = BASE_DIR / "data" / "inbox"
INBOX_DIR.mkdir(parents=True, exist_ok=True)

# GitHub-Upload legt Dateien oft flach ins Repo-Root — beide Layouts unterstützen.
if (BASE_DIR / "templates" / "impressum.html").is_file():
    TEMPLATE_DIR = BASE_DIR / "templates"
elif (BASE_DIR / "impressum.html").is_file():
    TEMPLATE_DIR = BASE_DIR
else:
    TEMPLATE_DIR = BASE_DIR / "templates"

app = Flask(
    __name__,
    static_folder=str(BASE_DIR),
    static_url_path="",
    template_folder=str(TEMPLATE_DIR),
)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB (Datei-Uploads)

MAX_ATTACHMENTS = 3
MAX_ATTACHMENT_BYTES = 8 * 1024 * 1024
MAX_ATTACHMENTS_TOTAL = 15 * 1024 * 1024
ALLOWED_ATTACHMENT_EXT = {
    ".pdf", ".jpg", ".jpeg", ".png", ".webp", ".heic",
    ".doc", ".docx", ".xls", ".xlsx",
}

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "").strip()
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASS = os.getenv("SMTP_PASS", "").strip()
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER).strip()
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
RESEND_FROM = os.getenv("RESEND_FROM", "Kaplan Solutions <onboarding@resend.dev>").strip()
REPLY_EMAIL = os.getenv("REPLY_EMAIL", "Kawa.f.Kaplan@gmail.com").strip()
COMPANY_PHONE = os.getenv("COMPANY_PHONE", "+49 159 01309199").strip()
SITE_URL = os.getenv("SITE_URL", "https://kaplan-solutions.onrender.com").strip().rstrip("/")
EMAIL_LOGO_URL = os.getenv("EMAIL_LOGO_URL", f"{SITE_URL}/email-logo.png")
SHEETS_WEBHOOK_URL = os.getenv("SHEETS_WEBHOOK_URL", "").strip()

ROLE_LABELS = {
    "bauherr": "Auftraggeber — sucht ein Bauunternehmen",
    "unternehmen": "Auftragnehmer — sucht Aufträge / Netzwerk",
}

BAUHER_FIELDS = [
    ("Projektart", "project"),
    ("Standort", "location"),
    ("Gewünschter Projektstart", "timeline"),
    ("Budgetrahmen", "budget"),
    ("Projektgröße", "project_size"),
    ("Aktueller Stand", "project_status"),
]

UNTERNEHMEN_FIELDS = [
    ("Firmenname", "company_name"),
    ("Gewerke / Spezialisierung", "trades"),
    ("Einsatzgebiet", "region"),
    ("Verfügbare Kapazität", "capacity"),
    ("Typischer Auftragsumfang", "order_scope"),
    ("Freie Baukapazität", "team_capacity"),
    ("Mitarbeiterzahl", "employees"),
    ("Referenzprojekte", "references"),
]


def uses_resend() -> bool:
    return bool(RESEND_API_KEY and ADMIN_EMAIL)


def email_configured() -> bool:
    if uses_resend():
        return True
    return bool(ADMIN_EMAIL and SMTP_USER and SMTP_PASS)


def is_valid_email(value: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value or ""))


def parse_attachments(data: dict) -> tuple[list[dict], str | None]:
    """Validiert Anhänge aus JSON [{filename, content}] → Resend-Format."""
    raw = data.get("attachments") or []
    if not raw:
        return [], None
    if not isinstance(raw, list):
        return [], "Ungültige Anhänge."
    if len(raw) > MAX_ATTACHMENTS:
        return [], f"Maximal {MAX_ATTACHMENTS} Dateien erlaubt."

    out: list[dict] = []
    total = 0
    for item in raw:
        if not isinstance(item, dict):
            return [], "Ungültige Anhänge."
        filename = (item.get("filename") or "").strip()
        content_b64 = (item.get("content") or "").strip()
        if not filename or not content_b64:
            return [], "Ungültige Anhänge."
        safe_name = Path(filename).name
        ext = Path(safe_name).suffix.lower()
        if ext not in ALLOWED_ATTACHMENT_EXT:
            return [], f"Dateityp nicht erlaubt: {ext or safe_name}"
        try:
            raw_bytes = base64.b64decode(content_b64, validate=True)
        except Exception:
            return [], f"Datei konnte nicht gelesen werden: {safe_name}"
        if len(raw_bytes) > MAX_ATTACHMENT_BYTES:
            return [], f"Datei zu groß (max. 8 MB): {safe_name}"
        total += len(raw_bytes)
        if total > MAX_ATTACHMENTS_TOTAL:
            return [], "Anhänge gesamt zu groß (max. 15 MB)."
        out.append({"filename": safe_name, "content": content_b64})

    return out, None


def save_inquiry(payload: dict) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = re.sub(r"[^\w\-]", "_", payload.get("name", "anfrage"))[:40]
    path = INBOX_DIR / f"{stamp}_{safe_name}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def notify_macos(title: str, message: str) -> None:
    if os.getenv("RENDER") or os.getenv("PRODUCTION"):
        return
    try:
        script = f'display notification "{message}" with title "{title}"'
        subprocess.run(["osascript", "-e", script], check=False, timeout=3)
    except Exception:
        pass


GOLD = "#b87333"
TEXT = "#1a1a1a"
MUTED = "#666666"


def _safe(s: str) -> str:
    return (
        str(s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _row(label: str, value: str) -> str:
    v = _safe((value or "").strip() or "—")
    return (
        f'<tr><td style="padding:12px 16px;background:#fafafa;color:#888888;'
        f'font-family:Arial,Helvetica,sans-serif;font-size:11px;letter-spacing:0.08em;'
        f'text-transform:uppercase;width:40%;border-bottom:1px solid #eeeeee;vertical-align:top">{label}</td>'
        f'<td style="padding:12px 16px;color:{TEXT};font-family:Arial,Helvetica,sans-serif;'
        f'font-size:15px;line-height:1.5;border-bottom:1px solid #eeeeee;vertical-align:top">{v}</td></tr>'
    )


def _email_wrap(inner_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f0f0f0">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f0f0f0;padding:32px 16px">
<tr><td align="center">
<table role="presentation" width="600" cellspacing="0" cellpadding="0" style="max-width:600px;width:100%;background:#ffffff">
{inner_html}
</table>
</td></tr>
</table>
</body></html>"""


def _email_brand_header(title: str) -> str:
    return f"""<tr><td style="padding:40px 40px 24px;border-bottom:1px solid #e8e8e8">
  <p style="margin:0 0 16px;font-family:Arial,Helvetica,sans-serif;font-size:11px;letter-spacing:0.35em;text-transform:uppercase;color:{GOLD}">Kaplan Solutions</p>
  <p style="margin:0;font-family:Georgia,'Times New Roman',serif;font-size:26px;font-weight:400;color:{TEXT};line-height:1.35">{_safe(title)}</p>
</td></tr>"""


def _email_footer_html() -> str:
    footer = _safe(company_footer_text()).replace("\n", "<br>")
    return f"""<tr><td style="padding:24px 40px 40px;border-top:1px solid #e8e8e8;font-family:Arial,Helvetica,sans-serif;font-size:13px;color:#888888;line-height:1.65">
  <p style="margin:0 0 4px;color:#666666">Mit freundlichen Grüßen</p>
  <p style="margin:0 0 12px;font-family:Georgia,'Times New Roman',serif;font-size:17px;color:{TEXT}">{_safe(COMPANY["brand"])}</p>
  <p style="margin:0;font-size:12px;color:#999999">{footer}</p>
</td></tr>"""


def _parse_location(text: str) -> tuple[str, str]:
    """Extrahiert Stadt und PLZ aus Standort/Gebiet."""
    raw = (text or "").strip()
    if not raw or raw == "—":
        return "—", ""
    m = re.search(r"\b(\d{5})\b", raw)
    plz = m.group(1) if m else ""
    city = raw
    if plz:
        city = re.sub(r".*?\b" + plz + r"\b\s*", "", raw).strip(" ,-")
        if not city:
            city = re.sub(r"\b\d{5}\b", "", raw).strip(" ,-")
    city = city.split(",")[0].strip() or raw
    return city[:80], plz


def _categorize_branche(text: str) -> str:
    raw = (text or "").strip().lower()
    if not raw or raw == "—":
        return "Sonstiges"
    rules = [
        ("Neubau", ("neubau", "neubau", "mehrfamilien", "einfamilienhaus", "neugestaltung")),
        ("Sanierung", ("sanierung", "renovierung", "modernisierung", "kernsanierung")),
        ("Rohbau", ("rohbau", "schalung", "betonbau")),
        ("Ausbau", ("ausbau", "innenausbau", "trockenbau", "innenausbau")),
        ("Tiefbau", ("tiefbau", "erdarbeiten", "straßenbau", "strassenbau")),
        ("Gewerbebau", ("gewerbe", "industrie", "halle", "logistik")),
        ("Wohnungsbau", ("wohnung", "wohnungsbau", "mfh", "efh")),
        ("Elektro", ("elektro", "elektrik", "photovoltaik", "pv")),
        ("SHK", ("shk", "sanitär", "heizung", "klima", "installateur")),
    ]
    for label, keys in rules:
        if any(k in raw for k in keys):
            return label
    return raw[:48].title()


def _fallback_ref() -> str:
    return f"KS-{datetime.now().strftime('%Y%m%d%H%M%S')}"


def _matches_email_html(matches: list) -> str:
    if not matches:
        return ""
    items = []
    for m in matches[:3]:
        score = m.get("score", 0)
        reason = _safe(m.get("reason", ""))
        name = _safe(m.get("name", ""))
        ref = _safe(m.get("ref", ""))
        email = _safe(m.get("email", ""))
        items.append(
            f'<li style="margin-bottom:14px;line-height:1.55;color:{MUTED}">'
            f'<strong style="color:{TEXT}">{name}</strong>'
            f' <span style="color:{GOLD}">({score}% Passung)</span><br>'
            f'Anfrage-Nr.: {ref} · {reason}<br>'
            f'<a href="mailto:{email}" style="color:{GOLD};text-decoration:none">{email}</a>'
            f"</li>"
        )
    return f"""<tr><td style="padding:0 40px 28px">
  <p style="margin:0 0 12px;font-family:Arial,Helvetica,sans-serif;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:{GOLD}">Empfohlene Partner (automatisch)</p>
  <ul style="margin:0;padding-left:18px;font-size:14px">{''.join(items)}</ul>
</td></tr>"""


def _matches_email_text(matches: list) -> list[str]:
    if not matches:
        return []
    lines = ["", "── EMPFOHLENE PARTNER (AUTOMATISCH) ──"]
    for m in matches[:3]:
        lines.append(
            f"• {m.get('name')} ({m.get('score')}% Passung) — {m.get('ref')}\n"
            f"  {m.get('reason')}\n"
            f"  {m.get('email')}"
        )
    return lines


def build_email_bodies(data: dict, role_label: str, now: str):
    name = data["name"]
    email = data["email"]
    ref = data.get("ref") or _fallback_ref()
    badge = "AUFTRAGGEBER" if data["role"] == "bauherr" else "AUFTRAGNEHMER"
    attachment_names = data.get("attachment_names") or []
    att_suffix = f" · {len(attachment_names)} Anhang/Anhänge" if attachment_names else ""
    subject = f"[LEAD · {ref} · {badge}{att_suffix}] {name} — Kaplan Solutions"
    matches = data.get("matches") or []

    rows_html = [
        _row("Anfrage-Nr.", ref),
        _row("Anfrageart", role_label),
        _row("Name", name),
        _row("E-Mail", email),
        _row("Telefon", data.get("phone", "—")),
        _row("Firma / Organisation", data.get("company", "—")),
    ]
    if data.get("branche"):
        rows_html.append(_row("Branche", data["branche"]))
    if data.get("stadt"):
        rows_html.append(_row("Stadt", data["stadt"]))

    rows_text = [
        "════════════════════════════════════════",
        "        KAPLAN SOLUTIONS · NEUE ANFRAGE",
        "════════════════════════════════════════",
        "",
        f"Anfrage-Nr.:    {ref}",
        f"Eingegangen:    {now}",
        f"Anfrageart:     {role_label}",
        "",
        "── KONTAKT ──",
        f"Name:           {name}",
        f"E-Mail:         {email}",
        f"Telefon:        {data.get('phone', '—')}",
        f"Firma:          {data.get('company', '—')}",
        "",
    ]
    if data.get("branche"):
        rows_text.append(f"Branche:        {data['branche']}")
    if data.get("stadt"):
        rows_text.append(f"Stadt:          {data['stadt']}")
    rows_text.append("")

    if data["role"] == "bauherr":
        section = "── PROJEKTDETAILS ──"
        rows_text.append(section)
        for label, key in BAUHER_FIELDS:
            val = data.get(key, "—")
            rows_text.append(f"{label + ':':<22} {val}")
            rows_html.append(_row(label, val))
    else:
        section = "── UNTERNEHMEN ──"
        rows_text.append(section)
        for label, key in UNTERNEHMEN_FIELDS:
            val = data.get(key, "—")
            rows_text.append(f"{label + ':':<22} {val}")
            rows_html.append(_row(label, val))

    message = data.get("message", "")
    attachment_names = data.get("attachment_names") or []
    if attachment_names:
        names = ", ".join(attachment_names)
        rows_html.append(_row("Anhänge", names))
        rows_text.extend(["", "── ANHÄNGE ──", names])

    folder_url = data.get("folder_url")
    if folder_url:
        rows_html.append(_row("Lead-Ordner", folder_url))
        rows_text.extend(["", "── LEAD-ORDNER ──", folder_url])

    rows_text.extend(_matches_email_text(matches))
    rows_text.extend([
        "",
        "── NACHRICHT ──",
        message or "—",
        "",
        "────────────────────────────────────────",
        f"Direkt antworten: {email}",
    ])

    text_body = "\n".join(rows_text)

    safe_message = _safe(message)
    inner = f"""{_email_brand_header("Neue Lead-Anfrage")}
<tr><td style="padding:8px 40px 20px">
  <span style="display:inline-block;padding:6px 14px;border:1px solid {GOLD};color:{GOLD};font-family:Arial,Helvetica,sans-serif;font-size:10px;letter-spacing:0.2em">{badge}</span>
  <span style="margin-left:12px;font-family:Arial,Helvetica,sans-serif;font-size:12px;color:#999999">{_safe(now)}</span>
</td></tr>
<tr><td style="padding:0 40px 28px">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border:1px solid #eeeeee">
{''.join(rows_html)}
</table>
</td></tr>
<tr><td style="padding:0 40px 28px">
  <p style="margin:0 0 12px;font-family:Arial,Helvetica,sans-serif;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:{GOLD}">Nachricht</p>
  <p style="margin:0;padding:16px 20px;background:#f7f7f7;border-left:3px solid {GOLD};color:{MUTED};font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.65;white-space:pre-wrap">{safe_message}</p>
</td></tr>
{_matches_email_html(matches)}
<tr><td style="padding:0 40px 32px;font-family:Arial,Helvetica,sans-serif;font-size:14px;text-align:center">
  <a href="mailto:{_safe(email)}" style="color:{GOLD};text-decoration:none">Direkt antworten: {_safe(email)}</a>
</td></tr>
{_email_footer_html()}"""

    html_body = _email_wrap(inner)

    return subject, text_body, html_body


def _send_resend(
    to: str,
    subject: str,
    text_body: str,
    html_body: str,
    reply_to: str | None = None,
    attachments: list[dict] | None = None,
) -> None:
    payload: dict = {
        "from": RESEND_FROM,
        "to": [to],
        "subject": subject,
        "html": html_body,
        "text": text_body,
    }
    if reply_to:
        payload["reply_to"] = reply_to
    if attachments:
        payload["attachments"] = attachments
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
            # Cloudflare vor api.resend.com blockt 'Python-urllib' (Error 1010).
            "User-Agent": "Mozilla/5.0 (compatible; KaplanSolutions/1.0; +https://kaplan-solutions.onrender.com)",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status >= 300:
                raise RuntimeError(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Resend Fehler ({exc.code}): {body}") from exc


def _send_smtp(to: str, subject: str, text_body: str, html_body: str, reply_to: str | None = None) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Kaplan Solutions <{FROM_EMAIL}>"
    msg["To"] = to
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(FROM_EMAIL, [to], msg.as_string())


def send_email(
    to: str,
    subject: str,
    text_body: str,
    html_body: str,
    reply_to: str | None = None,
    attachments: list[dict] | None = None,
) -> None:
    if uses_resend():
        _send_resend(to, subject, text_body, html_body, reply_to=reply_to, attachments=attachments)
    else:
        _send_smtp(to, subject, text_body, html_body, reply_to=reply_to)


def send_admin_email(
    subject: str,
    text_body: str,
    html_body: str,
    reply_to: str,
    attachments: list[dict] | None = None,
) -> None:
    send_email(ADMIN_EMAIL, subject, text_body, html_body, reply_to=reply_to, attachments=attachments)


def build_customer_confirmation(data: dict, role_label: str, now: str) -> tuple[str, str, str]:
    name = data["name"]
    ref = data.get("ref") or _fallback_ref()
    subject = f"Ihre Anfrage {ref} bei Kaplan Solutions — Eingang bestätigt"

    summary_lines = [f"Anfrage-Nr.: {ref}", f"Anfrageart: {role_label}"]
    if data["role"] == "bauherr":
        if data.get("project"):
            summary_lines.append(f"Projektart: {data['project']}")
        if data.get("location"):
            summary_lines.append(f"Standort: {data['location']}")
        if data.get("timeline"):
            summary_lines.append(f"Geplanter Start: {data['timeline']}")
    else:
        company = data.get("company_name") or data.get("company")
        if company and company != "—":
            summary_lines.append(f"Unternehmen: {company}")
        if data.get("trades"):
            summary_lines.append(f"Gewerke: {data['trades']}")
        if data.get("region"):
            summary_lines.append(f"Einsatzgebiet: {data['region']}")

    attachment_names = data.get("attachment_names") or []
    if attachment_names:
        summary_lines.append(
            f"Anhänge ({len(attachment_names)}): {', '.join(attachment_names)}"
        )

    summary_text = "\n".join(f"  • {line}" for line in summary_lines)

    text_body = f"""Sehr geehrte/r {name},

vielen Dank für Ihre Anfrage bei Kaplan Solutions.

Wir bestätigen den Eingang Ihrer Nachricht am {now}.
Ihre Anfrage-Nr. lautet: {ref}
Ihre Angaben wurden an unser Team weitergeleitet. Ein fachkundiger Ansprechpartner meldet sich in der Regel innerhalb von 24 Stunden persönlich bei Ihnen.

Ihre Angaben im Überblick:
{summary_text}

Bei Rückfragen erreichen Sie uns unter:
E-Mail: {REPLY_EMAIL}
Telefon: {COMPANY_PHONE}

Mit freundlichen Grüßen

{company_footer_text()}
www.kaplan-solutions.de

—
Diese E-Mail wurde automatisch erstellt. Bitte antworten Sie nicht direkt auf diese Nachricht.
Für Rückfragen nutzen Sie: {REPLY_EMAIL}
"""

    summary_html = "".join(
        f'<li style="margin-bottom:8px;color:{MUTED}">{_safe(line)}</li>' for line in summary_lines
    )

    inner = f"""{_email_brand_header("Eingang Ihrer Anfrage bestätigt")}
<tr><td style="padding:32px 40px;font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.75;color:{MUTED}">
  <p style="margin:0 0 20px;color:{TEXT}">Sehr geehrte/r {_safe(name)},</p>
  <p style="margin:0 0 20px">vielen Dank für Ihr Vertrauen in <strong style="color:{TEXT}">Kaplan Solutions</strong>. Wir bestätigen hiermit den Eingang Ihrer Anfrage am <strong style="color:{GOLD}">{_safe(now)}</strong>.</p>
  <p style="margin:0 0 20px">Ihre Anfrage-Nr.: <strong style="color:{GOLD}">{_safe(ref)}</strong></p>
  <p style="margin:0 0 28px">Ihre Angaben wurden an unser Team weitergeleitet. Ein fachkundiger Ansprechpartner wird sich <strong style="color:{TEXT}">zeitnah — in der Regel innerhalb von 24 Stunden</strong> — persönlich bei Ihnen melden.</p>

  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f7f7f7;border:1px solid #ebebeb;margin-bottom:28px">
  <tr><td style="padding:20px 24px">
    <p style="margin:0 0 12px;font-family:Arial,Helvetica,sans-serif;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:{GOLD}">Ihre Angaben im Überblick</p>
    <ul style="margin:0;padding-left:18px;font-size:14px;line-height:1.65">{summary_html}</ul>
  </td></tr>
  </table>

  <p style="margin:0 0 8px;font-family:Arial,Helvetica,sans-serif;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:#999999">Kontakt</p>
  <p style="margin:0;font-size:14px;color:{MUTED}">
    E-Mail: <a href="mailto:{_safe(REPLY_EMAIL)}" style="color:{GOLD};text-decoration:none">{_safe(REPLY_EMAIL)}</a><br>
    Telefon: <span style="color:{TEXT}">{_safe(COMPANY_PHONE)}</span>
  </p>
</td></tr>
<tr><td style="padding:0 40px 24px;font-family:Arial,Helvetica,sans-serif;font-size:11px;color:#aaaaaa;line-height:1.5">
  Diese Nachricht wurde automatisch erstellt. Für Rückfragen: <a href="mailto:{_safe(REPLY_EMAIL)}" style="color:{GOLD};text-decoration:none">{_safe(REPLY_EMAIL)}</a>
</td></tr>
{_email_footer_html()}"""

    html_body = _email_wrap(inner)

    return subject, text_body, html_body


def send_customer_confirmation(data: dict, role_label: str, now: str) -> None:
    subject, text_body, html_body = build_customer_confirmation(data, role_label, now)
    send_email(data["email"], subject, text_body, html_body, reply_to=REPLY_EMAIL)


def _sheet_fields(payload: dict) -> dict:
    """Vereinheitlicht beide Rollen auf gemeinsame Spalten für die Google-Tabelle."""
    is_bau = payload.get("role") == "bauherr"
    company = payload.get("company", "")
    if not is_bau:
        company = payload.get("company_name") or company
    loc_raw = payload.get("location", "") if is_bau else payload.get("region", "")
    stadt, plz = _parse_location(loc_raw)
    branche_raw = payload.get("project", "") if is_bau else payload.get("trades", "")
    branche = _categorize_branche(branche_raw)
    return {
        "role_code": "bauherr" if is_bau else "unternehmen",
        "eingegangen": payload.get("timestamp", ""),
        "rolle": "Auftraggeber" if is_bau else "Auftragnehmer",
        "name": payload.get("name", ""),
        "email": payload.get("email", ""),
        "telefon": payload.get("phone", ""),
        "firma": company,
        "branche": branche,
        "stadt": stadt,
        "plz": plz,
        "projekt": branche_raw or (payload.get("project", "") if is_bau else payload.get("trades", "")),
        "standort": loc_raw,
        "zeitrahmen": payload.get("timeline", "") if is_bau else payload.get("capacity", ""),
        "budget": payload.get("budget", "") if is_bau else payload.get("order_scope", ""),
        "groesse": payload.get("project_size", "") if is_bau else payload.get("team_capacity", ""),
        "status_feld": payload.get("project_status", "") if is_bau else payload.get("employees", ""),
        "referenzen": "" if is_bau else payload.get("references", ""),
        "nachricht": payload.get("message", ""),
        "dateien": ", ".join(payload.get("attachment_names") or []) or "—",
        "bearbeitung": "Neu",
    }


def forward_to_sheet(payload: dict) -> dict:
    """Schreibt Lead in Google-Tabelle; gibt ref, matches, folder_url zurück."""
    url = os.getenv("SHEETS_WEBHOOK_URL", "").strip()
    if not url:
        return {}
    if not url.rstrip("/").endswith("/exec"):
        print("[sheet] SHEETS_WEBHOOK_URL muss mit /exec enden", flush=True)
        return {}
    try:
        body = json.dumps(_sheet_fields(payload)).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; KaplanSolutions/1.0)",
        }

        def _post(target: str) -> str:
            req = urllib.request.Request(
                target, data=body, headers=headers, method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = resp.read().decode("utf-8", errors="replace")
                if result and '"ok":false' in result.replace(" ", ""):
                    raise RuntimeError(result[:300])
                return result

        try:
            raw = _post(url)
        except urllib.error.HTTPError as exc:
            if exc.code in (301, 302, 303, 307, 308):
                redirect = exc.headers.get("Location")
                if not redirect:
                    raise
                raw = _post(redirect)
            else:
                raise
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}
    except Exception as exc:
        print(f"[sheet] Weiterleitung in Google-Tabelle übersprungen: {exc}", flush=True)
        return {}


def apply_sheet_meta(payload: dict) -> None:
    """Reichert Payload mit Anfrage-Nr., Matches und Ordner-Link an."""
    meta = forward_to_sheet(payload)
    payload["ref"] = meta.get("ref") or _fallback_ref()
    payload["matches"] = meta.get("matches") or []
    if meta.get("folder_url"):
        payload["folder_url"] = meta["folder_url"]
    payload["stadt"] = _parse_location(
        payload.get("location", "") if payload.get("role") == "bauherr" else payload.get("region", "")
    )[0]
    payload["branche"] = _categorize_branche(
        payload.get("project", "") if payload.get("role") == "bauherr" else payload.get("trades", "")
    )


def validate_inquiry(data: dict) -> str | None:
    role = (data.get("role") or "").strip()
    if role not in ROLE_LABELS:
        return "Bitte wählen Sie eine Anfrageart."
    if not (data.get("name") or "").strip():
        return "Bitte geben Sie Ihren Namen an."
    if not is_valid_email((data.get("email") or "").strip()):
        return "Bitte geben Sie eine gültige E-Mail an."
    if not (data.get("message") or "").strip():
        return "Bitte ergänzen Sie die zusätzlichen Angaben."
    if not data.get("privacy_consent"):
        return "Bitte bestätigen Sie die Datenschutzerklärung."

    if role == "bauherr":
        for label, key in BAUHER_FIELDS:
            if not (data.get(key) or "").strip():
                return f"Bitte ausfüllen: {label}"
    else:
        for label, key in UNTERNEHMEN_FIELDS:
            if key == "employees" or key == "references":
                continue
            if not (data.get(key) or "").strip():
                return f"Bitte ausfüllen: {label}"
    return None


@app.route("/assets/<path:filename>")
def serve_asset(filename):
    nested = BASE_DIR / "assets" / filename
    if nested.is_file():
        return send_from_directory(BASE_DIR / "assets", filename)
    flat = BASE_DIR / filename
    if flat.is_file():
        return send_from_directory(BASE_DIR, filename)
    abort(404)


@app.route("/data/references.json")
def serve_references():
    nested = BASE_DIR / "data" / "references.json"
    flat = BASE_DIR / "references.json"
    if nested.is_file():
        return send_from_directory(
            BASE_DIR / "data", "references.json", mimetype="application/json"
        )
    if flat.is_file():
        return send_from_directory(
            BASE_DIR, "references.json", mimetype="application/json"
        )
    abort(404)


@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


def legal_context(active: str) -> dict:
    return {
        "c": COMPANY,
        "active": active,
        "updated": "19. Mai 2026",
        "year": datetime.now().year,
    }


@app.route("/impressum")
def impressum():
    return render_template("impressum.html", **legal_context("impressum"))


@app.route("/datenschutz")
def datenschutz():
    return render_template("datenschutz.html", **legal_context("datenschutz"))


@app.route("/agb")
def agb():
    return render_template("agb.html", **legal_context("agb"))


@app.post("/api/send-confirmation")
def send_confirmation():
    """Kunden-Bestätigung per Resend/SMTP (optional, wenn Server konfiguriert)."""
    data = request.get_json(silent=True) or {}
    role = (data.get("role") or "").strip()
    if role not in ROLE_LABELS:
        return jsonify({"ok": False, "error": "Ungültige Anfrageart."}), 400
    email = (data.get("email") or "").strip()
    if not is_valid_email(email):
        return jsonify({"ok": False, "error": "Ungültige E-Mail."}), 400

    if not email_configured():
        return jsonify({"ok": False, "error": "E-Mail nicht konfiguriert."}), 503

    role_label = ROLE_LABELS[role]
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    payload = {
        "role": role,
        "name": (data.get("name") or "").strip() or "Kunde",
        "email": email,
        "phone": data.get("phone", ""),
        "company": data.get("company", ""),
        "message": data.get("message", ""),
        "project": data.get("project", ""),
        "location": data.get("location", ""),
        "timeline": data.get("timeline", ""),
        "company_name": data.get("company_name", ""),
        "trades": data.get("trades", ""),
        "region": data.get("region", ""),
    }

    try:
        send_customer_confirmation(payload, role_label, now)
    except Exception:
        return jsonify({"ok": False, "error": "Bestätigung konnte nicht gesendet werden."}), 500

    return jsonify({"ok": True})


@app.post("/api/contact")
def contact():
    data = request.get_json(silent=True) or {}

    err = validate_inquiry(data)
    if err:
        return jsonify({"ok": False, "error": err}), 400

    attachments, att_err = parse_attachments(data)
    if att_err:
        return jsonify({"ok": False, "error": att_err}), 400

    role = data["role"].strip()
    role_label = ROLE_LABELS[role]
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    payload = {
        "timestamp": now,
        "role": role,
        "role_label": role_label,
        "name": data.get("name", "").strip(),
        "email": data.get("email", "").strip(),
        "phone": data.get("phone", "").strip() or "—",
        "company": data.get("company", "").strip() or "—",
        "message": data.get("message", "").strip(),
        "privacy_consent": bool(data.get("privacy_consent")),
    }

    if role == "bauherr":
        for _, key in BAUHER_FIELDS:
            payload[key] = (data.get(key) or "").strip()
        payload["project"] = payload.get("project", "")
    else:
        for _, key in UNTERNEHMEN_FIELDS:
            payload[key] = (data.get(key) or "").strip() or "—"
        payload["project"] = payload.get("trades", "")

    if attachments:
        payload["attachment_names"] = [a["filename"] for a in attachments]

    save_inquiry(payload)
    apply_sheet_meta(payload)

    if not email_configured():
        notify_macos("Kaplan Solutions", f"Neue Anfrage gespeichert: {payload['name']}")
        err = (
            "E-Mail ist auf dem Server noch nicht eingerichtet. "
            "Bitte SMTP-Zugangsdaten im Hosting-Dashboard (Render → Environment) eintragen."
            if os.getenv("RENDER")
            else "E-Mail ist noch nicht eingerichtet. Bitte setup_email.sh ausführen oder .env prüfen."
        )
        return jsonify({"ok": False, "error": err}), 503

    subject, text_body, html_body = build_email_bodies(payload, role_label, now)

    log_line = f"{datetime.now().isoformat()} | OK | {payload['name']} | {payload['email']}\n"
    try:
        send_admin_email(subject, text_body, html_body, payload["email"], attachments=attachments or None)
        send_customer_confirmation(payload, role_label, now)
        (BASE_DIR / "data" / "contact.log").open("a", encoding="utf-8").write(
            log_line.replace("| OK |", "| OK + Bestätigung |")
        )
    except smtplib.SMTPAuthenticationError:
        notify_macos("Kaplan Solutions", f"Anfrage von {payload['name']} — Gmail-Login fehlgeschlagen")
        return jsonify({
            "ok": False,
            "error": "Gmail-Anmeldung fehlgeschlagen. App-Passwort in .env prüfen.",
        }), 500
    except Exception:
        return jsonify({
            "ok": False,
            "error": "E-Mail konnte nicht gesendet werden. Anfrage wurde lokal gespeichert.",
        }), 500

    notify_macos("Kaplan Solutions", f"Neue Anfrage von {payload['name']}")
    return jsonify({
        "ok": True,
        "message": "Anfrage wurde gesendet.",
        "ref": payload.get("ref"),
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    if not email_configured():
        print("\n  ⚠  E-Mail: Bitte einmal ausführen →  ./setup_email.sh\n")
    else:
        print(f"\n  ✓  Anfragen per E-Mail an: {ADMIN_EMAIL}\n")
        print(f"  ✓  Backup-Ordner: {INBOX_DIR}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
