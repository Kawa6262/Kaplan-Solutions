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

if TYPE_CHECKING:
    import types

logger = logging.getLogger(__name__)

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
RESEND_FROM = os.getenv(
    "RESEND_FROM", "Kaplan Solutions <onboarding@resend.dev>"
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
    to: str, subject: str, text_body: str, html_body: str, reply_to: str | None = None
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
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
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
    to: str, subject: str, text_body: str, html_body: str, reply_to: str | None = None
) -> None:
    if uses_resend():
        send_resend(to, subject, text_body, html_body, reply_to=reply_to)
    else:
        send_smtp(to, subject, text_body, html_body, reply_to=reply_to)


def install(server: types.ModuleType) -> None:
    """Ersetzt E-Mail-Funktionen in server.py (ohne server.py auf GitHub zu tauschen)."""

    def send_admin_email(subject, text_body, html_body, reply_to: str) -> None:
        send_email(ADMIN_EMAIL, subject, text_body, html_body, reply_to=reply_to)

    server.send_email = send_email
    server.send_admin_email = send_admin_email
    server.email_configured = email_configured
    server.uses_resend = uses_resend

    mode = "Resend" if uses_resend() else "SMTP"
    print(f"[mailer] E-Mail-Modus: {mode} → {ADMIN_EMAIL or '(ADMIN_EMAIL fehlt)'}", flush=True)
