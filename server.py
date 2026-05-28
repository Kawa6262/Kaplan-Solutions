#!/usr/bin/env python3
"""Kaplan Solutions — Website + Kontaktformular per E-Mail."""

import json
import os
import re
import smtplib
import ssl
import subprocess
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

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "").strip()
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASS = os.getenv("SMTP_PASS", "").strip()
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER).strip()
REPLY_EMAIL = os.getenv("REPLY_EMAIL", "kontakt@kaplan-solutions.de").strip()
COMPANY_PHONE = os.getenv("COMPANY_PHONE", "+49 159 01309199").strip()
SITE_URL = os.getenv("SITE_URL", "https://kaplan-solutions.onrender.com").strip().rstrip("/")
EMAIL_LOGO_URL = os.getenv("EMAIL_LOGO_URL", f"{SITE_URL}/email-logo.png")

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


def email_configured() -> bool:
    return bool(ADMIN_EMAIL and SMTP_USER and SMTP_PASS)


def is_valid_email(value: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value or ""))


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


def _row(label: str, value: str) -> str:
    v = (value or "").strip() or "—"
    safe = (
        str(v)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return (
        f'<tr><td style="padding:10px 14px;background:#141414;color:#737373;'
        f'font-family:Arial,sans-serif;font-size:11px;letter-spacing:0.1em;'
        f'text-transform:uppercase;width:38%;border-bottom:1px solid #262626">{label}</td>'
        f'<td style="padding:10px 14px;background:#0a0a0a;color:#f5f5f5;'
        f'font-family:Arial,sans-serif;font-size:14px;border-bottom:1px solid #262626">{safe}</td></tr>'
    )


def _email_header_html(title: str, subtitle: str = "") -> str:
    sub = (
        f'<p style="margin:8px 0 0;font-family:Arial,sans-serif;font-size:12px;color:#737373">{subtitle}</p>'
        if subtitle
        else ""
    )
    return f"""<tr><td style="padding:32px 36px 24px;border-bottom:1px solid #262626;text-align:center">
  <img src="{EMAIL_LOGO_URL}" alt="Kaplan Solutions" width="280" height="50"
       style="display:block;margin:0 auto 16px;max-width:100%;height:auto;border:0" />
  <p style="margin:0;font-family:Georgia,'Times New Roman',serif;font-size:22px;color:#f5f5f5;font-weight:400">{title}</p>
  {sub}
</td></tr>"""


def build_email_bodies(data: dict, role_label: str, now: str):
    name = data["name"]
    email = data["email"]
    badge = "AUFTRAGGEBER" if data["role"] == "bauherr" else "AUFTRAGNEHMER"
    subject = f"[LEAD · {badge}] {name} — Kaplan Solutions"

    rows_html = [
        _row("Anfrageart", role_label),
        _row("Name", name),
        _row("E-Mail", email),
        _row("Telefon", data.get("phone", "—")),
        _row("Firma / Organisation", data.get("company", "—")),
    ]

    rows_text = [
        "════════════════════════════════════════",
        "        KAPLAN SOLUTIONS · NEUE ANFRAGE",
        "════════════════════════════════════════",
        "",
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
    rows_text.extend([
        "",
        "── NACHRICHT ──",
        message or "—",
        "",
        "────────────────────────────────────────",
        f"Direkt antworten: {email}",
    ])

    text_body = "\n".join(rows_text)

    html_body = f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f0f0f0">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f0f0f0;padding:28px 12px">
<tr><td align="center">
<table role="presentation" width="600" cellspacing="0" cellpadding="0" style="max-width:600px;width:100%;background:#0a0a0a">
{_email_header_html("Neue Lead-Anfrage", now)}
<tr><td style="padding:8px 36px 16px;text-align:center">
  <span style="display:inline-block;padding:6px 14px;border:1px solid #b87333;color:#b87333;font-family:Arial,sans-serif;font-size:10px;letter-spacing:0.2em">{badge}</span>
</td></tr>
<tr><td style="padding:0 36px 28px">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border:1px solid #262626">
{''.join(rows_html)}
</table>
</td></tr>
<tr><td style="padding:0 36px 32px">
  <p style="margin:0 0 10px;font-family:Arial,sans-serif;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:#b87333">Nachricht</p>
  <p style="margin:0;padding:16px 18px;background:#141414;border-left:3px solid #b87333;color:#d4d4d4;font-family:Arial,sans-serif;font-size:14px;line-height:1.65;white-space:pre-wrap">{message}</p>
</td></tr>
<tr><td style="padding:20px 36px 32px;border-top:1px solid #262626;font-family:Arial,sans-serif;font-size:12px;color:#737373;text-align:center">
  <a href="mailto:{email}" style="color:#b87333;text-decoration:none">Direkt antworten: {email}</a>
</td></tr>
</table>
</td></tr>
</table>
</body></html>"""

    return subject, text_body, html_body


def send_email(to: str, subject: str, text_body: str, html_body: str, reply_to: str | None = None) -> None:
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


def send_admin_email(subject: str, text_body: str, html_body: str, reply_to: str) -> None:
    send_email(ADMIN_EMAIL, subject, text_body, html_body, reply_to=reply_to)


def build_customer_confirmation(data: dict, role_label: str, now: str) -> tuple[str, str, str]:
    name = data["name"]
    subject = "Ihre Anfrage bei Kaplan Solutions — Eingang bestätigt"

    summary_lines = [f"Anfrageart: {role_label}"]
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

    summary_text = "\n".join(f"  • {line}" for line in summary_lines)

    text_body = f"""Sehr geehrte/r {name},

vielen Dank für Ihre Anfrage bei Kaplan Solutions.

Wir bestätigen den Eingang Ihrer Nachricht am {now}. Ihre Angaben wurden an unser Team weitergeleitet. Ein fachkundiger Ansprechpartner meldet sich in der Regel innerhalb von 24 Stunden persönlich bei Ihnen.

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

    summary_html = "".join(f"<li style=\"margin-bottom:6px\">{line}</li>" for line in summary_lines)

    html_body = f"""<!DOCTYPE html>
<html lang="de">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f0f0f0;font-family:Georgia,'Times New Roman',serif">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f0f0f0;padding:32px 16px">
<tr><td align="center">
<table role="presentation" width="600" cellspacing="0" cellpadding="0" style="max-width:600px;width:100%;background:#0a0a0a;color:#f5f5f5">

{_email_header_html("Eingang Ihrer Anfrage bestätigt", now)}

<tr><td style="padding:32px 40px;font-family:Arial,sans-serif;font-size:15px;line-height:1.75;color:#d4d4d4">
  <p style="margin:0 0 20px;color:#f5f5f5">Sehr geehrte/r {name},</p>
  <p style="margin:0 0 20px">vielen Dank für Ihr Vertrauen in <strong style="color:#f5f5f5">Kaplan Solutions</strong>. Wir bestätigen hiermit den Eingang Ihrer Anfrage am <strong style="color:#b87333">{now}</strong>.</p>
  <p style="margin:0 0 28px">Ihre Angaben wurden an unser Team weitergeleitet. Ein fachkundiger Ansprechpartner wird sich <strong style="color:#f5f5f5">zeitnah — in der Regel innerhalb von 24 Stunden</strong> — persönlich bei Ihnen melden.</p>

  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#141414;border:1px solid #262626;margin-bottom:28px">
  <tr><td style="padding:20px 24px">
    <p style="margin:0 0 12px;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:#b87333">Ihre Angaben im Überblick</p>
    <ul style="margin:0;padding-left:18px;color:#a3a3a3;font-size:14px;line-height:1.6">{summary_html}</ul>
  </td></tr>
  </table>

  <p style="margin:0 0 8px;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:#737373">Kontakt</p>
  <p style="margin:0;font-size:14px;color:#a3a3a3">
    E-Mail: <a href="mailto:{REPLY_EMAIL}" style="color:#b87333;text-decoration:none">{REPLY_EMAIL}</a><br>
    Telefon: <span style="color:#f5f5f5">{COMPANY_PHONE}</span>
  </p>
</td></tr>

<tr><td style="padding:24px 40px 40px;border-top:1px solid #262626;font-family:Arial,sans-serif;font-size:13px;color:#737373;line-height:1.6">
  <p style="margin:0 0 4px;color:#a3a3a3">Mit freundlichen Grüßen</p>
  <p style="margin:0 0 8px;font-family:Georgia,serif;font-size:16px;color:#f5f5f5">{COMPANY["brand"]}</p>
  <p style="margin:0;font-size:12px">{company_footer_text().replace(chr(10), "<br>")}</p>
  <p style="margin:20px 0 0;font-size:11px;color:#525252">Diese Nachricht wurde automatisch erstellt. Für Rückfragen wenden Sie sich bitte an {REPLY_EMAIL}.</p>
</td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""

    return subject, text_body, html_body


def send_customer_confirmation(data: dict, role_label: str, now: str) -> None:
    subject, text_body, html_body = build_customer_confirmation(data, role_label, now)
    send_email(data["email"], subject, text_body, html_body, reply_to=REPLY_EMAIL)


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

    save_inquiry(payload)

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
        send_admin_email(subject, text_body, html_body, payload["email"])
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
    return jsonify({"ok": True, "message": "Anfrage wurde gesendet."})


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    if not email_configured():
        print("\n  ⚠  E-Mail: Bitte einmal ausführen →  ./setup_email.sh\n")
    else:
        print(f"\n  ✓  Anfragen per E-Mail an: {ADMIN_EMAIL}\n")
        print(f"  ✓  Backup-Ordner: {INBOX_DIR}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
