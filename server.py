#!/usr/bin/env python3
"""Kaplan Solutions — Website + Kontaktformular per E-Mail."""

import base64
import json
import os
import re
import smtplib
import ssl
import subprocess
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from flask import Flask, abort, jsonify, redirect, render_template, request, send_from_directory

from company_config import COMPANY, company_footer_text
from email_deliverability import deliverability_headers
from provisions_config import PROVISIONS

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

# ── Spam-Schutz (Honeypot + Rate-Limit) ──────────────────────────────────────
HONEYPOT_FIELD = "company_website"  # verstecktes Feld; nur Bots füllen es aus
RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", "5"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "600"))  # Sekunden
_rate_log: dict[str, list[float]] = defaultdict(list)


def client_ip() -> str:
    """Echte Client-IP (hinter Render/Proxy via X-Forwarded-For)."""
    fwd = request.headers.get("X-Forwarded-For", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.remote_addr or "unknown"


def is_honeypot_spam(data: dict) -> bool:
    """True, wenn das versteckte Honeypot-Feld ausgefüllt wurde (= Bot)."""
    return bool((data.get(HONEYPOT_FIELD) or "").strip())


def is_rate_limited(ip: str) -> bool:
    """True, wenn die IP im Zeitfenster bereits zu viele erfolgreiche
    Absendungen hatte. Zählt NICHT mit (nur Lese-Prüfung)."""
    now = time.time()
    hits = [t for t in _rate_log[ip] if now - t < RATE_LIMIT_WINDOW]
    _rate_log[ip] = hits
    return len(hits) >= RATE_LIMIT_MAX


def record_submission(ip: str) -> None:
    """Vermerkt eine erfolgreiche Absendung für das Rate-Limit."""
    _rate_log[ip].append(time.time())


def _is_explicit_junk_name(name: str) -> bool:
    name = (name or "").strip()
    if not name:
        return False
    if re.search(r"test[\-\s]?anfrage", name, re.I):
        return True
    if re.match(r"^(max|maria|peter|anna)\s+mustermann$", name, re.I):
        return True
    if re.match(r"^(test|testing|dummy|fake|asdf|xxx)$", name, re.I):
        return True
    return False


def _looks_like_real_lead(data: dict) -> bool:
    """Schutznetz: ausführliche Anfragen nie als Junk werten."""
    message = (data.get("message") or "").strip()
    phone = re.sub(r"\D", "", data.get("phone") or data.get("telefon") or "")
    budget = (data.get("budget") or "").strip()
    timeline = (data.get("timeline") or data.get("zeitrahmen") or "").strip()
    project = (data.get("project") or data.get("projekt") or "").strip()
    location = (
        (data.get("location") or "")
        or (data.get("standort") or "")
        or (data.get("stadt") or "")
    ).strip()

    if len(message) >= 45:
        return True
    if len(phone) >= 9 and len(message) >= 18:
        return True
    if project and timeline and budget and budget not in ("—", "-", ""):
        return True
    if len(location) >= 4 and len(message) >= 25 and len(phone) >= 9:
        return True
    return False


def is_junk_lead(data: dict) -> tuple[bool, list[str]]:
    """Konservative Junk-Erkennung — lieber Test behalten als echten Lead löschen."""
    name = (data.get("name") or "").strip()

    if _is_explicit_junk_name(name):
        return True, ["name:test-anfrage"]

    if _looks_like_real_lead(data):
        return False, []

    email = (data.get("email") or "").strip().lower()
    message = (data.get("message") or "").strip()
    msg_lower = message.lower()
    strong: list[str] = []
    weak: list[str] = []

    if not name and not email:
        strong.append("leer")

    if re.search(
        r"^test@|@example\.(com|org|de)|mailinator|yopmail|tempmail|"
        r"guerrillamail|10minutemail|discard\.|trashmail",
        email,
        re.I,
    ):
        strong.append("email:wegwerf")

    if re.match(
        r"^(test|nur test|dies ist ein test|bitte ignorieren|ignore this|"
        r"formular test|testeintrag|nur ein test)\.?$",
        msg_lower,
        re.I,
    ):
        strong.append("nachricht:explizit-test")

    if data.get("is_test") or data.get("test_lead"):
        strong.append("flag:test")

    admin = os.getenv("ADMIN_EMAIL", "").strip().lower()
    if admin and email == admin and re.search(
        r"test[\-\s]?anfrage|nur test|formular test",
        f"{name} {msg_lower}",
        re.I,
    ):
        strong.append("admin:self-test")

    if re.match(r"^(test|probe|dummy)\b", name, re.I) and len(name) < 35:
        weak.append("name:test-prefix")
    if re.search(r"\b(mustermann|musterfrau|john doe|jane doe|lorem ipsum)\b", f"{name} {msg_lower}", re.I):
        weak.append("dummy-text")
    if re.search(r"\btest\b", msg_lower) and len(msg_lower) < 35:
        weak.append("nachricht:enthaelt-test")

    if strong:
        return True, strong
    if len(weak) >= 2:
        return True, weak
    return False, weak


def spam_response(data: dict):
    """Prüft Honeypot + Rate-Limit VOR der Verarbeitung. Gibt eine fertige
    Flask-Antwort zurück (oder None, wenn die Anfrage in Ordnung ist)."""
    if is_honeypot_spam(data):
        ip = client_ip()
        print(f"[spam] Honeypot ausgelöst — IP {ip} blockiert", flush=True)
        # Bot soll glauben, es habe geklappt → kein erneuter Versuch.
        return jsonify({"ok": True, "message": "Anfrage wurde gesendet."}), 200
    if is_rate_limited(client_ip()):
        print(f"[spam] Rate-Limit erreicht — IP {client_ip()}", flush=True)
        return jsonify({
            "ok": False,
            "error": "Zu viele Anfragen in kurzer Zeit. Bitte versuchen Sie es in einigen Minuten erneut.",
        }), 429
    return None

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "").strip()
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASS = os.getenv("SMTP_PASS", "").strip()
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER).strip()
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
RESEND_FROM = os.getenv(
    "RESEND_FROM", "Kaplan Solutions <kontakt@kaplan-solutions.de>"
).strip()
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


def _row_link(label: str, url: str) -> str:
    u = (url or "").strip()
    safe = _safe(u)
    inner = (
        f'<a href="{safe}" style="color:{GOLD};text-decoration:none;word-break:break-all">{safe}</a>'
        if u
        else "—"
    )
    return (
        f'<tr><td style="padding:12px 16px;background:#fafafa;color:#888888;'
        f'font-family:Arial,Helvetica,sans-serif;font-size:11px;letter-spacing:0.08em;'
        f'text-transform:uppercase;width:40%;border-bottom:1px solid #eeeeee;vertical-align:top">{label}</td>'
        f'<td style="padding:12px 16px;color:{TEXT};font-family:Arial,Helvetica,sans-serif;'
        f'font-size:15px;line-height:1.5;border-bottom:1px solid #eeeeee;vertical-align:top">{inner}</td></tr>'
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
        body = (
            f'<p style="margin:0;color:{MUTED};font-size:14px;line-height:1.55">'
            f"Aktuell keine passende Gegenanfrage in der Datenbank "
            f"(Matching startet ab Score 35% bei Stadt, Branche und Region)."
            f"</p>"
        )
    else:
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
        body = f'<ul style="margin:0;padding-left:18px;font-size:14px">{"".join(items)}</ul>'
    return f"""<tr><td style="padding:0 40px 28px">
  <p style="margin:0 0 12px;font-family:Arial,Helvetica,sans-serif;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:{GOLD}">Empfohlene Partner (automatisch)</p>
  {body}
</td></tr>"""


def _matches_email_text(matches: list) -> list[str]:
    lines = ["", "── EMPFOHLENE PARTNER (AUTOMATISCH) ──"]
    if not matches:
        lines.append(
            "Keine passende Gegenanfrage gefunden "
            "(Matching ab 35% bei Stadt, Branche, Region)."
        )
        return lines
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
    if data.get("callback_slot"):
        rows_html.append(_row("Rückruf-Termin", data["callback_slot"]))
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
    if data.get("callback_slot"):
        rows_text.append(f"Rückruf-Termin: {data['callback_slot']}")
        rows_text.append("")
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
    rows_html.append(_row_link("Lead-Ordner (Google Drive)", folder_url or ""))
    rows_text.extend([
        "",
        "── LEAD-ORDNER (GOOGLE DRIVE) ──",
        folder_url or "— (wird nachgereicht, falls Sheet-Webhook langsam war)",
    ])

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
    reply = reply_to or REPLY_EMAIL
    if reply:
        payload["reply_to"] = reply
    payload["headers"] = deliverability_headers(recipient=to)
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
    if data.get("callback_slot"):
        summary_lines.append(f"Rückruf-Termin: {data['callback_slot']}")

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
Ihre Angaben wurden an unser Team weitergeleitet. Ein fachkundiger Ansprechpartner meldet sich zeitnah persönlich bei Ihnen.

Ihre Angaben im Überblick:
{summary_text}

Bei Rückfragen erreichen Sie uns unter:
E-Mail: {REPLY_EMAIL}
Telefon: {COMPANY_PHONE}

Mit freundlichen Grüßen

{company_footer_text()}
www.kaplan-solutions.de

—
Bei Rückfragen antworten Sie einfach auf diese E-Mail — wir lesen mit.
Alternativ: {REPLY_EMAIL} · {COMPANY_PHONE}
"""

    summary_html = "".join(
        f'<li style="margin-bottom:8px;color:{MUTED}">{_safe(line)}</li>' for line in summary_lines
    )

    inner = f"""{_email_brand_header("Eingang Ihrer Anfrage bestätigt")}
<tr><td style="padding:32px 40px;font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.75;color:{MUTED}">
  <p style="margin:0 0 20px;color:{TEXT}">Sehr geehrte/r {_safe(name)},</p>
  <p style="margin:0 0 20px">vielen Dank für Ihr Vertrauen in <strong style="color:{TEXT}">Kaplan Solutions</strong>. Wir bestätigen hiermit den Eingang Ihrer Anfrage am <strong style="color:{GOLD}">{_safe(now)}</strong>.</p>
  <p style="margin:0 0 20px">Ihre Anfrage-Nr.: <strong style="color:{GOLD}">{_safe(ref)}</strong></p>
  <p style="margin:0 0 28px">Ihre Angaben wurden an unser Team weitergeleitet. Ein fachkundiger Ansprechpartner meldet sich <strong style="color:{TEXT}">zeitnah persönlich</strong> bei Ihnen.</p>

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
  Bei Rückfragen antworten Sie einfach auf diese E-Mail — wir lesen mit.
  Alternativ: <a href="mailto:{_safe(REPLY_EMAIL)}" style="color:{GOLD};text-decoration:none">{_safe(REPLY_EMAIL)}</a>
</td></tr>
{_email_footer_html()}"""

    html_body = _email_wrap(inner)

    return subject, text_body, html_body


def send_customer_confirmation(data: dict, role_label: str, now: str) -> None:
    subject, text_body, html_body = build_customer_confirmation(data, role_label, now)
    send_email(data["email"], subject, text_body, html_body, reply_to=REPLY_EMAIL)
    try:
        from lead_followup import schedule_followup

        schedule_followup(data, role_label)
    except Exception as exc:
        print(f"[lead_followup] Follow-up nicht geplant: {exc}", flush=True)


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
        "rueckruf": payload.get("callback_slot", "") or "—",
        "dateien": ", ".join(payload.get("attachment_names") or []) or "—",
        "bearbeitung": "Neu",
        "lead_source": payload.get("lead_source", "") or payload.get("utm_source", "") or "Website",
        "utm_source": payload.get("utm_source", ""),
        "utm_medium": payload.get("utm_medium", ""),
        "utm_campaign": payload.get("utm_campaign", ""),
    }


def _parse_sheet_json(raw: str) -> dict:
    """Parst JSON aus Apps-Script-Antwort (auch wenn HTML drumherum liegt)."""
    raw = (raw or "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return {}
    try:
        data = json.loads(m.group(0))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def forward_to_sheet(payload: dict) -> dict:
    """Schreibt Lead in Google-Tabelle; gibt ref, matches, folder_url zurück."""
    url = os.getenv("SHEETS_WEBHOOK_URL", "").strip()
    if not url:
        print("[sheet] SHEETS_WEBHOOK_URL fehlt", flush=True)
        return {}
    if not url.rstrip("/").endswith("/exec"):
        print("[sheet] SHEETS_WEBHOOK_URL muss mit /exec enden", flush=True)
        return {}

    body = json.dumps(_sheet_fields(payload)).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; KaplanSolutions/1.0)",
    }
    # Hoher Timeout, aber nur EIN Versuch: ein Retry würde bei langsamer
    # (aber erfolgreicher) Apps-Script-Verarbeitung einen doppelten Lead anlegen.
    timeout = int(os.getenv("SHEETS_WEBHOOK_TIMEOUT", "90"))
    attempts = int(os.getenv("SHEETS_WEBHOOK_RETRIES", "1"))

    def _post(target: str) -> str:
        req = urllib.request.Request(target, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = resp.read().decode("utf-8", errors="replace")
            if result and '"ok":false' in result.replace(" ", ""):
                raise RuntimeError(result[:300])
            return result

    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
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
            meta = _parse_sheet_json(raw)
            if meta.get("ok"):
                if meta.get("junk") or meta.get("skipped"):
                    print(
                        f"[sheet] Junk-Lead verworfen: {meta.get('reasons', meta.get('reason', ''))}",
                        flush=True,
                    )
                    return meta
                print(
                    f"[sheet] OK ref={meta.get('ref')} matches={len(meta.get('matches') or [])} "
                    f"folder={'ja' if meta.get('folder_url') else 'nein'} attempt={attempt}",
                    flush=True,
                )
                return meta
            print(f"[sheet] Antwort ohne ok:true: {raw[:200]}", flush=True)
            return meta
        except Exception as exc:
            last_exc = exc
            print(f"[sheet] Versuch {attempt}/{attempts} fehlgeschlagen: {exc}", flush=True)

    print(f"[sheet] Alle Versuche fehlgeschlagen: {last_exc}", flush=True)
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
    try:
        from trust_score import schedule_trust_check

        schedule_trust_check(payload)
    except Exception as exc:
        print(f"[trust] Hintergrund-Prüfung nicht gestartet: {exc}", flush=True)

    _maybe_alert_hot_matches(payload)


def _build_match_payload(payload: dict, m: dict, ref: str, role: str) -> dict:
    ag_ref = ref if role == "bauherr" else (m.get("ref") or "")
    an_ref = (m.get("ref") or "") if role == "bauherr" else ref
    if role == "bauherr":
        ag_name = payload.get("name") or ""
        ag_email = payload.get("email") or ""
        ag_firma = payload.get("company") or ag_name
        ag_phone = payload.get("phone") or ""
        an_name = m.get("name") or ""
        an_email = m.get("email") or ""
        an_firma = m.get("name") or ""
        an_phone = ""
    else:
        an_name = payload.get("name") or ""
        an_email = payload.get("email") or ""
        an_firma = payload.get("company") or an_name
        an_phone = payload.get("phone") or ""
        ag_name = m.get("name") or ""
        ag_email = m.get("email") or ""
        ag_firma = m.get("name") or ""
        ag_phone = ""
    match_id = "__".join(sorted([ag_ref, an_ref]))
    return {
        "match_id": match_id,
        "score": int(m.get("score") or 0),
        "ag_ref": ag_ref,
        "ag_name": ag_name,
        "ag_firma": ag_firma,
        "ag_email": ag_email,
        "ag_phone": ag_phone,
        "an_ref": an_ref,
        "an_name": an_name,
        "an_firma": an_firma,
        "an_email": an_email,
        "an_phone": an_phone,
        "stadt": payload.get("stadt") or m.get("stadt") or "",
        "branche": payload.get("branche") or m.get("branche") or "",
        "reasons": m.get("reason") or m.get("reasons") or "",
        "folder_url": payload.get("folder_url") or "",
    }


def _maybe_alert_hot_matches(payload: dict) -> None:
    """Sofort-Alert wenn Sheet bei Lead-Eingang heiße Matches meldet."""
    matches = payload.get("matches") or []
    if not matches:
        return
    role = payload.get("role") or ""
    ref = payload.get("ref") or ""
    if not ref or role not in ("bauherr", "partner"):
        return

    from matching.alerts import process_match_alert
    from matching.config import MATCH_ALERT_MIN_SCORE, MATCH_BRIEFING_EMAIL

    admin = MATCH_BRIEFING_EMAIL or os.getenv("ADMIN_EMAIL", "").strip()
    if not admin:
        return

    for m in matches:
        if int(m.get("score") or 0) < MATCH_ALERT_MIN_SCORE:
            continue
        match = _build_match_payload(payload, m, ref, role)
        try:
            result = process_match_alert(match, admin_email=admin)
            print(f"[match-alert] {match['match_id']}: {result}", flush=True)
        except Exception as exc:
            print(f"[match-alert] Fehler {match.get('match_id')}: {exc}", flush=True)


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


STATS_FILE = BASE_DIR / "data" / "stats.json"


def record_view(page: str = "home") -> None:
    """Zählt Seitenaufrufe — ohne Cookies, ohne IP-Speicherung."""
    try:
        stats = json.loads(STATS_FILE.read_text(encoding="utf-8"))
    except Exception:
        stats = {"total": 0, "days": {}, "pages": {}}
    today = datetime.now().strftime("%Y-%m-%d")
    stats["total"] = int(stats.get("total", 0)) + 1
    days = stats.setdefault("days", {})
    days[today] = int(days.get(today, 0)) + 1
    pages = stats.setdefault("pages", {})
    page_days = pages.setdefault(page, {})
    page_days[today] = int(page_days.get(today, 0)) + 1
    if len(days) > 120:
        for old in sorted(days)[:-90]:
            days.pop(old, None)
    try:
        STATS_FILE.write_text(json.dumps(stats), encoding="utf-8")
    except Exception:
        pass


@app.route("/")
def index():
    record_view("home")
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/bauherr")
def bauherr_landing():
    record_view("bauherr")
    return send_from_directory(BASE_DIR, "bauherr.html")


@app.route("/partner")
def partner_redirect():
    """Kurzlink für Partner-Outreach — Formular voreingestellt auf Auftragnehmer."""
    record_view("partner")
    qs = request.query_string.decode("utf-8")
    if qs:
        target = f"/?role=unternehmen&{qs}#contact"
    else:
        target = (
            "/?role=unternehmen&utm_source=outreach&utm_medium=email"
            "&utm_campaign=partner#contact"
        )
    return redirect(target, code=302)


@app.route("/kostenlos")
def kostenlos_redirect():
    qs = request.query_string.decode("utf-8")
    target = "/bauherr" + (f"?{qs}" if qs else "")
    return redirect(target, code=302)


@app.route("/empfehlung")
def empfehlung_redirect():
    """Kurzlink für WhatsApp-Empfehlungen (z. B. Baufirma-Netzwerk)."""
    record_view("empfehlung")
    return redirect(
        "/bauherr?utm_source=whatsapp&utm_medium=empfehlung&utm_campaign=baufirma-netzwerk",
        code=302,
    )


@app.route("/api/stats")
def stats_view():
    """Einfache Besucher-Statistik (mit ?key=… schützbar via STATS_TOKEN)."""
    token = os.getenv("STATS_TOKEN", "").strip()
    if token and request.args.get("key", "") != token:
        abort(403)
    try:
        stats = json.loads(STATS_FILE.read_text(encoding="utf-8"))
    except Exception:
        stats = {"total": 0, "days": {}}
    days = stats.get("days", {})
    today = datetime.now().strftime("%Y-%m-%d")
    cutoff = (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d")
    last7 = sum(v for k, v in days.items() if k >= cutoff)
    return jsonify({
        "gesamt": stats.get("total", 0),
        "heute": days.get(today, 0),
        "letzte_7_tage": last7,
        "pro_tag": dict(sorted(days.items())[-30:]),
    })


def legal_context(active: str) -> dict:
    return {
        "c": COMPANY,
        "p": PROVISIONS,
        "active": active,
        "updated": "24. Juni 2026",
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


@app.route("/provisionsmodell")
def provisionsmodell():
    return render_template("provisionsmodell.html", **legal_context("provisionsmodell"))


@app.route("/vermittlungsvertrag")
def vermittlungsvertrag():
    return render_template("vermittlungsvertrag.html", **legal_context("vermittlungsvertrag"))


@app.route("/vermittlungsvertrag/partner")
def vermittlungsvertrag_partner():
    return render_template(
        "vermittlungsvertrag_partner.html",
        **legal_context("vermittlungsvertrag"),
    )


@app.route("/vermittlungsvertrag/bauherr")
def vermittlungsvertrag_bauherr():
    return render_template(
        "vermittlungsvertrag_bauherr.html",
        **legal_context("vermittlungsvertrag"),
    )


def _valid_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))


def _record_unsubscribe(email: str) -> None:
    try:
        from outreach import storage
        storage.init_db()
        storage.add_unsubscribe(email)
    except Exception as exc:
        print(f"[abmelden] Outreach-DB übersprungen: {exc}", flush=True)


@app.route("/abmelden", methods=["GET", "POST"])
def abmelden():
    """Abmeldung von Outreach-Mails (inkl. Gmail One-Click per RFC 8058)."""
    ctx = legal_context("abmelden")
    email = (request.args.get("email") or request.form.get("email") or "").strip().lower()

    if request.method == "POST":
        one_click = (
            request.headers.get("List-Unsubscribe") == "One-Click"
            or request.form.get("List-Unsubscribe") == "One-Click"
        )
        if one_click and email and _valid_email(email):
            _record_unsubscribe(email)
            return "", 200
        if email and _valid_email(email):
            _record_unsubscribe(email)
            return render_template("abmelden.html", success=True, email=email, **ctx)

    return render_template("abmelden.html", success=False, email=email, **ctx)


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

    blocked = spam_response(data)
    if blocked is not None:
        return blocked

    err = validate_inquiry(data)
    if err:
        return jsonify({"ok": False, "error": err}), 400

    junk, junk_reasons = is_junk_lead(data)
    if junk:
        print(
            f"[junk] Lead verworfen ({', '.join(junk_reasons)}): "
            f"{data.get('name', '')} <{data.get('email', '')}>",
            flush=True,
        )
        return jsonify({"ok": True, "message": "Anfrage wurde gesendet.", "junk": True})

    record_submission(client_ip())

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
        "callback_slot": (data.get("callback_slot") or "").strip() or "—",
        "message": data.get("message", "").strip(),
        "privacy_consent": bool(data.get("privacy_consent")),
        "lead_source": (data.get("lead_source") or data.get("utm_source") or "website").strip(),
        "utm_source": (data.get("utm_source") or "").strip(),
        "utm_medium": (data.get("utm_medium") or "").strip(),
        "utm_campaign": (data.get("utm_campaign") or "").strip(),
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
        "folder_url": payload.get("folder_url"),
        "matches": payload.get("matches") or [],
    })


@app.post("/api/match-alert")
def api_match_alert():
    """Sofort-Alert bei heißem Match (Google Apps Script / intern)."""
    from matching.config import MATCH_ALERT_SECRET, MATCH_BRIEFING_EMAIL
    from matching.alerts import process_match_alert

    secret = MATCH_ALERT_SECRET
    if not secret:
        abort(503)
    token = (
        request.headers.get("X-Match-Alert-Secret", "").strip()
        or request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    )
    if token != secret:
        abort(401)

    data = request.get_json(silent=True) or {}
    match = data.get("match") or data
    admin = (data.get("admin_email") or MATCH_BRIEFING_EMAIL or os.getenv("ADMIN_EMAIL", "")).strip()
    if not admin:
        return jsonify({"ok": False, "error": "admin_email fehlt"}), 400

    try:
        result = process_match_alert(match, admin_email=admin)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.post("/api/cron/lead-followups")
def cron_lead_followups():
    """Backup-Job (Render Cron / extern): Follow-ups nachplanen & fällige senden."""
    secret = os.getenv("CRON_SECRET", "").strip()
    if not secret:
        abort(503)
    token = (
        request.headers.get("X-Cron-Secret", "").strip()
        or request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    )
    if token != secret:
        abort(401)
    from lead_followup.reconcile import run_maintenance

    result = run_maintenance()
    return jsonify({"ok": True, **result})


def _cron_auth_ok() -> bool:
    secret = os.getenv("CRON_SECRET", "").strip()
    if not secret:
        return False
    token = (
        request.headers.get("X-Cron-Secret", "").strip()
        or request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    )
    return token == secret


@app.post("/api/cron/outreach")
def cron_outreach():
    """Outreach-Zyklus in der Cloud (Render Cron → Web-Service)."""
    if not _cron_auth_ok():
        abort(401)
    try:
        from outreach.runner import run_cycle

        run_cycle()
        from outreach import storage

        storage.init_db()
        summary = storage.stats_summary()
        return jsonify({"ok": True, "today_sent": summary.get("today_sent", 0), "queued": summary.get("queued", 0)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.post("/api/cron/billing")
def cron_billing():
    """Automatische Rechnungen für fällige Partner-Leads."""
    if not _cron_auth_ok():
        abort(401)
    from billing.runner import process_due_invoices

    result = process_due_invoices()
    return jsonify(result)


@app.post("/api/crm/invoice")
def api_crm_invoice():
    """Rechnung manuell für einen Partner-Lead generieren."""
    if not _crm_auth_ok():
        abort(401)
    data = request.get_json(silent=True) or {}
    ref = (data.get("ref") or "").strip()
    force = bool(data.get("force"))
    if not ref:
        return jsonify({"ok": False, "error": "ref fehlt"}), 400
    snap = _sheet_action("crm_snapshot")
    if not snap.get("ok"):
        return jsonify(snap), 502
    lead = next((l for l in (snap.get("leads") or []) if l.get("ref") == ref), None)
    if not lead:
        return jsonify({"ok": False, "error": "Lead nicht gefunden"}), 404
    from billing.runner import generate_and_send_invoice

    result = generate_and_send_invoice(lead, force=force)
    return jsonify(result)


# ── CRM Admin (Pipeline-Steuerung) ───────────────────────────────────────────

ADMIN_CRM_SECRET = os.getenv("ADMIN_CRM_SECRET", "").strip()


def _crm_auth_ok() -> bool:
    if not ADMIN_CRM_SECRET:
        return False
    token = (
        request.headers.get("X-Admin-Crm-Secret", "").strip()
        or request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    )
    return token == ADMIN_CRM_SECRET


def _sheet_action(action: str, extra: dict | None = None) -> dict:
    """Apps-Script-Aktion mit CRM-Secret."""
    payload = {"action": action, "crm_secret": ADMIN_CRM_SECRET}
    if extra:
        payload.update(extra)
    url = os.getenv("SHEETS_WEBHOOK_URL", "").strip()
    if not url or not ADMIN_CRM_SECRET:
        return {"ok": False, "error": "CRM nicht konfiguriert (SHEETS_WEBHOOK_URL / ADMIN_CRM_SECRET)"}
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; KaplanSolutions-CRM/1.0)",
    }
    timeout = int(os.getenv("SHEETS_WEBHOOK_TIMEOUT", "90"))
    try:
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return _parse_sheet_json(resp.read().decode("utf-8", errors="replace"))
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@app.route("/admin/crm")
def admin_crm_page():
    """Passwort-geschütztes CRM-Dashboard (Mac + iPhone)."""
    if not ADMIN_CRM_SECRET:
        abort(503)
    return render_template("admin_crm.html")


@app.get("/api/crm/snapshot")
def api_crm_snapshot():
    if not _crm_auth_ok():
        abort(401)
    resp = jsonify(_sheet_action("crm_snapshot"))
    r = app.make_response(resp)
    r.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return r


@app.post("/api/crm/update")
def api_crm_update():
    if not _crm_auth_ok():
        abort(401)
    data = request.get_json(silent=True) or {}
    ref = (data.get("ref") or "").strip()
    if not ref:
        return jsonify({"ok": False, "error": "ref fehlt"}), 400
    fields = data.get("fields") or data.get("updates") or {}
    result = _sheet_action("crm_update", {"ref": ref, "fields": fields})
    if result.get("ok") and fields.get("vertrag") == "Ja":
        try:
            from matching.intro_retry import try_intro_after_contract

            admin = os.getenv("ADMIN_EMAIL", "").strip()
            intro = try_intro_after_contract(ref, admin)
            if intro:
                result["intro_auto"] = intro
        except Exception as exc:
            result["intro_auto"] = {"ok": False, "error": str(exc)}
    return jsonify(result)


@app.post("/api/crm/activity")
def api_crm_activity_create():
    if not _crm_auth_ok():
        abort(401)
    data = request.get_json(silent=True) or {}
    return jsonify(_sheet_action("crm_activity_create", data))


@app.patch("/api/crm/activity/<activity_id>")
def api_crm_activity_update(activity_id: str):
    if not _crm_auth_ok():
        abort(401)
    data = request.get_json(silent=True) or {}
    data["id"] = activity_id
    return jsonify(_sheet_action("crm_activity_update", data))


@app.post("/api/crm/opportunity")
def api_crm_opportunity_update():
    if not _crm_auth_ok():
        abort(401)
    data = request.get_json(silent=True) or {}
    return jsonify(_sheet_action("crm_opportunity_update", data))


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    if not email_configured():
        print("\n  ⚠  E-Mail: Bitte einmal ausführen →  ./setup_email.sh\n")
    else:
        print(f"\n  ✓  Anfragen per E-Mail an: {ADMIN_EMAIL}\n")
        print(f"  ✓  Backup-Ordner: {INBOX_DIR}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
