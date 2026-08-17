"""Eingehende Mails über Resend (ohne Strato-Postfach)."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime
from email.utils import parseaddr
from zoneinfo import ZoneInfo

from crm.mail_inbox import DB_PATH, _conn, _guess_crm_ref

TZ = ZoneInfo("Europe/Berlin")

_AUTO_SUBJECT = re.compile(
    r"(automatische? antwort|abwesenh|out of office|autoreply|auto-reply|"
    r"urlaub|nicht im haus|delivery status|undeliverable|unzustellbar|"
    r"mail delivery failed|returned mail)",
    re.IGNORECASE,
)
_AUTO_SENDER = re.compile(
    r"(mailer-daemon|postmaster|no-?reply|noreply|bounce|do-?not-?reply)",
    re.IGNORECASE,
)


def _api_key() -> str:
    return os.getenv("RESEND_API_KEY", "").strip()


def configured() -> bool:
    return bool(_api_key())


def config_status() -> dict:
    return {
        "resend_inbound": configured(),
        "mode": "resend" if configured() else "none",
    }


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_api_key()}",
        "User-Agent": "Mozilla/5.0 (compatible; KaplanSolutions/1.0; +https://kaplan-solutions.de)",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _api(method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"https://api.resend.com{path}",
        data=data,
        headers=_headers(),
        method=method,
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else {}


def _is_automatic(sender: str, subject: str) -> bool:
    return bool(_AUTO_SENDER.search(sender) or _AUTO_SUBJECT.search(subject))


def _store(
    *,
    message_id: str,
    from_email: str,
    from_name: str,
    subject: str,
    body: str,
    received_at: str,
    in_reply_to: str | None = None,
) -> bool:
    if not from_email or _is_automatic(from_email, subject):
        return False
    crm_ref = _guess_crm_ref(subject, body)
    now = datetime.now(TZ).isoformat(timespec="seconds")
    db = _conn()
    try:
        cur = db.execute(
            """
            INSERT OR IGNORE INTO inbox_messages
            (message_id, from_email, from_name, subject, body, received_at, synced_at, crm_ref, in_reply_to)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message_id,
                from_email,
                from_name,
                subject,
                body[:8000],
                received_at,
                now,
                crm_ref or None,
                (in_reply_to or "")[:200] or None,
            ),
        )
        db.commit()
        return cur.rowcount > 0
    finally:
        db.close()


def ingest_email_id(email_id: str) -> bool:
    """Resend Received Email in CRM-DB speichern."""
    email_id = (email_id or "").strip()
    if not email_id or not configured():
        return False
    try:
        detail = _api("GET", f"/emails/receiving/{email_id}")
    except urllib.error.HTTPError:
        return False

    msg_id = (detail.get("message_id") or f"resend-{email_id}").strip()
    raw_from = detail.get("from") or ""
    from_name, from_email = parseaddr(raw_from)
    if not from_email and "@" in raw_from:
        from_email = raw_from.strip().lower()
    from_email = from_email.strip().lower()
    subject = (detail.get("subject") or "").strip()
    body = (detail.get("text") or detail.get("html") or "").strip()
    if detail.get("html") and not detail.get("text"):
        body = re.sub(r"<[^>]+>", " ", body)
    received = (detail.get("created_at") or datetime.now(TZ).isoformat())[:19]
    if "T" in received and "+" not in received and "Z" not in received:
        received = received.replace("T", " ")
    return _store(
        message_id=msg_id,
        from_email=from_email,
        from_name=from_name,
        subject=subject,
        body=body,
        received_at=received,
    )


def handle_webhook(event: dict) -> dict:
    if (event.get("type") or "") != "email.received":
        return {"ok": True, "ignored": True}
    data = event.get("data") or {}
    email_id = data.get("email_id") or data.get("id")
    if not email_id:
        return {"ok": False, "error": "email_id fehlt"}
    new = ingest_email_id(email_id)
    return {"ok": True, "new": new, "email_id": email_id}


def sync_resend_inbox(limit: int = 40) -> dict:
    if not configured():
        return {"ok": False, "error": "RESEND_API_KEY fehlt", **config_status()}

    new_count = 0
    try:
        listing = _api("GET", f"/emails/receiving?limit={min(limit, 100)}")
    except urllib.error.HTTPError as exc:
        err = exc.read().decode(errors="replace")[:200]
        return {"ok": False, "error": f"Resend API: {exc.code} {err}", **config_status()}

    for item in listing.get("data") or []:
        eid = item.get("id")
        if eid and ingest_email_id(eid):
            new_count += 1

    db = _conn()
    total = db.execute("SELECT COUNT(*) FROM inbox_messages").fetchone()[0]
    db.close()
    return {"ok": True, "new": new_count, "total": total, **config_status()}
