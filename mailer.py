"""Resend-E-Mail für Render Free (Gmail-SMTP ist dort blockiert)."""

from __future__ import annotations

import json
import logging
import os
import smtplib
import ssl
import urllib.error
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import TYPE_CHECKING

from email_deliverability import deliverability_headers

if TYPE_CHECKING:
    import types

logger = logging.getLogger(__name__)

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
RESEND_FROM = os.getenv(
    "RESEND_FROM", "Kaplan Solutions <kontakt@kaplan-solutions.de>"
).strip()
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "").strip()
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASS = os.getenv("SMTP_PASS", "").strip().replace(" ", "")
FROM_EMAIL = (os.getenv("FROM_EMAIL", SMTP_USER).strip() or SMTP_USER)
if SMTP_USER and "gmail" in SMTP_HOST and not RESEND_API_KEY:
    FROM_EMAIL = SMTP_USER


def uses_resend() -> bool:
    return bool(RESEND_API_KEY)


def email_configured() -> bool:
    if uses_resend():
        return bool(ADMIN_EMAIL)
    return bool(ADMIN_EMAIL and SMTP_USER and SMTP_PASS)


def send_resend(
    to: str,
    subject: str,
    text_body: str,
    html_body: str,
    reply_to: str | None = None,
    attachments: list[dict] | None = None,
    scheduled_at: str | None = None,
) -> str | None:
    payload: dict = {
        "from": RESEND_FROM,
        "to": [to],
        "subject": subject,
        "html": html_body,
        "text": text_body,
    }
    reply = reply_to or os.getenv("REPLY_EMAIL", "").strip()
    if reply:
        payload["reply_to"] = reply
    payload["headers"] = deliverability_headers(recipient=to)
    if attachments:
        payload["attachments"] = attachments
    if scheduled_at:
        payload["scheduled_at"] = scheduled_at
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
            body = resp.read().decode("utf-8", errors="replace")
            if resp.status >= 300:
                raise RuntimeError(body)
            try:
                data = json.loads(body) if body else {}
                return data.get("id")
            except json.JSONDecodeError:
                return None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Resend Fehler ({exc.code}): {body}") from exc


def send_smtp(
    to: str, subject: str, text_body: str, html_body: str, reply_to: str | None = None
) -> None:
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
        send_resend(to, subject, text_body, html_body, reply_to=reply_to, attachments=attachments)
    else:
        send_smtp(to, subject, text_body, html_body, reply_to=reply_to)


def send_email_scheduled(
    to: str,
    subject: str,
    text_body: str,
    html_body: str,
    scheduled_for,
    reply_to: str | None = None,
) -> str | None:
    """Plant E-Mail via Resend (ISO-Zeit). Nur mit Resend verfügbar."""
    if not uses_resend():
        raise RuntimeError("Geplante Mails erfordern Resend.")
    from zoneinfo import ZoneInfo

    dt = scheduled_for
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("Europe/Berlin"))
    scheduled_at = dt.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")
    return send_resend(
        to,
        subject,
        text_body,
        html_body,
        reply_to=reply_to,
        scheduled_at=scheduled_at,
    )


def _friendly_error(exc: Exception) -> str:
    msg = str(exc)
    if uses_resend():
        low = msg.lower()
        # WICHTIG: Empfänger-Beschränkung VOR dem 401/403-Check prüfen,
        # sonst wird ein 403 (Empfänger) fälschlich als "Key ungültig" gemeldet.
        if (
            "only send" in low
            or "testing emails" in low
            or "verify a domain" in low
            or "your own email" in low
        ):
            return (
                "Resend-Free sendet nur an Ihre eigene Resend-Adresse. "
                f"Original: {msg[:300]}"
            )
        if "401" in msg or ("invalid" in low and "key" in low) or "api key" in low:
            return (
                "Resend-API-Key ungültig oder abgelaufen. "
                "In Render → Environment neuen Key von resend.com eintragen."
            )
        return f"Resend-Fehler (Original): {msg[:400]}"
    return "E-Mail konnte nicht gesendet werden. Anfrage wurde lokal gespeichert."


def install(server: types.ModuleType) -> None:
    """Ersetzt E-Mail-Funktionen in server.py (ohne server.py auf GitHub zu tauschen)."""

    def send_admin_email(subject, text_body, html_body, reply_to: str, attachments=None) -> None:
        send_email(ADMIN_EMAIL, subject, text_body, html_body, reply_to=reply_to, attachments=attachments)

    original_confirmation = server.send_customer_confirmation

    def send_customer_confirmation_safe(data, role_label, now) -> None:
        try:
            original_confirmation(data, role_label, now)
        except Exception as exc:
            print(f"[mailer] Bestätigungs-Mail optional — übersprungen: {exc}", flush=True)

    server.send_email = send_email
    server.send_admin_email = send_admin_email
    server.send_customer_confirmation = send_customer_confirmation_safe
    server.email_configured = email_configured
    server.uses_resend = uses_resend

    def contact_patched():
        from flask import jsonify, request

        data = request.get_json(silent=True) or {}

        blocked = server.spam_response(data)
        if blocked is not None:
            return blocked

        err = server.validate_inquiry(data)
        if err:
            return jsonify({"ok": False, "error": err}), 400

        server.record_submission(server.client_ip())

        attachments, att_err = server.parse_attachments(data)
        if att_err:
            return jsonify({"ok": False, "error": att_err}), 400

        role = data["role"].strip()
        role_label = server.ROLE_LABELS[role]
        now = server.datetime.now().strftime("%d.%m.%Y %H:%M")

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
        }

        if role == "bauherr":
            for _, key in server.BAUHER_FIELDS:
                payload[key] = (data.get(key) or "").strip()
            payload["project"] = payload.get("project", "")
        else:
            for _, key in server.UNTERNEHMEN_FIELDS:
                payload[key] = (data.get(key) or "").strip() or "—"
            payload["project"] = payload.get("trades", "")

        if attachments:
            payload["attachment_names"] = [a["filename"] for a in attachments]

        server.save_inquiry(payload)
        try:
            server.apply_sheet_meta(payload)
        except Exception as exc:
            print(f"[mailer] Google-Tabelle übersprungen: {exc}", flush=True)

        if not email_configured():
            err_msg = (
                "E-Mail ist auf dem Server noch nicht eingerichtet. "
                "Bitte RESEND_API_KEY und ADMIN_EMAIL in Render → Environment eintragen."
                if os.getenv("RENDER")
                else "E-Mail ist noch nicht eingerichtet."
            )
            return jsonify({"ok": False, "error": err_msg}), 503

        subject, text_body, html_body = server.build_email_bodies(
            payload, role_label, now
        )
        log_line = (
            f"{server.datetime.now().isoformat()} | OK | {payload['name']} | {payload['email']}\n"
        )

        try:
            send_admin_email(subject, text_body, html_body, payload["email"], attachments=attachments or None)
        except smtplib.SMTPAuthenticationError:
            return jsonify({
                "ok": False,
                "error": "Gmail-Anmeldung fehlgeschlagen. App-Passwort prüfen.",
            }), 500
        except Exception as exc:
            print(f"[mailer] Admin-Mail fehlgeschlagen: {exc}", flush=True)
            return jsonify({"ok": False, "error": _friendly_error(exc)}), 500

        send_customer_confirmation_safe(payload, role_label, now)
        try:
            (server.BASE_DIR / "data" / "contact.log").open("a", encoding="utf-8").write(
                log_line
            )
        except Exception:
            pass

        server.notify_macos("Kaplan Solutions", f"Neue Anfrage von {payload['name']}")
        return jsonify({
            "ok": True,
            "message": "Anfrage wurde gesendet.",
            "ref": payload.get("ref"),
            "folder_url": payload.get("folder_url"),
            "matches": payload.get("matches") or [],
        })

    contact_patched.__name__ = "contact"
    server.contact = contact_patched
    server.app.view_functions["contact"] = contact_patched

    mode = "Resend" if uses_resend() else "SMTP"
    key_hint = "gesetzt" if RESEND_API_KEY else "FEHLT"
    print(
        f"[mailer] E-Mail-Modus: {mode} | ADMIN={ADMIN_EMAIL or 'FEHLT'} | API-Key={key_hint}",
        flush=True,
    )
