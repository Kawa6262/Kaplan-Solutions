"""Assistent-Chat in Kaplan Sales — Befehle & Antworten (Handy ↔ Cursor)."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from company_config import company_footer_text
from lead_followup.config import REPLY_EMAIL

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "crm_comms.db"
TZ = ZoneInfo("Europe/Berlin")


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS copilot_messages (
            id TEXT PRIMARY KEY,
            role TEXT NOT NULL,
            text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            meta TEXT,
            pending_agent INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_copilot_created ON copilot_messages(created_at);
        """
    )
    return db


def _now() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def list_messages(*, since_id: str | None = None, limit: int = 80) -> dict:
    db = _conn()
    if since_id:
        row = db.execute("SELECT created_at FROM copilot_messages WHERE id = ?", (since_id,)).fetchone()
        if row:
            rows = db.execute(
                """
                SELECT id, role, text, created_at, pending_agent
                FROM copilot_messages WHERE created_at > ?
                ORDER BY created_at ASC LIMIT ?
                """,
                (row["created_at"], limit),
            ).fetchall()
        else:
            rows = []
    else:
        rows = db.execute(
            """
            SELECT id, role, text, created_at, pending_agent
            FROM copilot_messages ORDER BY created_at DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        rows = list(reversed(rows))
    pending = db.execute(
        "SELECT COUNT(*) FROM copilot_messages WHERE pending_agent = 1 AND role = 'user'"
    ).fetchone()[0]
    db.close()
    return {"ok": True, "messages": [dict(r) for r in rows], "pending_agent": pending}


def add_message(*, role: str, text: str, meta: dict | None = None, pending_agent: bool = False) -> dict:
    text = (text or "").strip()
    if not text:
        return {"ok": False, "error": "Leere Nachricht"}
    msg_id = str(uuid.uuid4())
    db = _conn()
    db.execute(
        """
        INSERT INTO copilot_messages (id, role, text, created_at, meta, pending_agent)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            msg_id,
            role,
            text,
            _now(),
            json.dumps(meta or {}, ensure_ascii=False),
            1 if pending_agent else 0,
        ),
    )
    db.commit()
    db.close()
    return {"ok": True, "id": msg_id, "role": role, "text": text}


def clear_pending(user_message_id: str) -> None:
    db = _conn()
    db.execute(
        "UPDATE copilot_messages SET pending_agent = 0 WHERE id = ?",
        (user_message_id,),
    )
    db.commit()
    db.close()


def _notify_admin(text: str) -> None:
    admin = os.getenv("ADMIN_EMAIL", "").strip()
    if not admin:
        return
    try:
        from mailer import email_configured, send_email

        if not email_configured():
            return
        subject = "Kaplan Sales — neuer Befehl"
        body = f"""Neue Nachricht im Assistenten (Kaplan Sales):

{text}

---
Antworten: Cursor öffnen → Assistent liest data/crm_comms.db
Oder direkt in Kaplan Sales unter „Assistent" warten.

{company_footer_text()}
"""
        send_email(admin, subject, body, f"<pre style='font-family:monospace'>{text}</pre>", mail_kind="transactional")
    except Exception:
        pass


def _auto_status() -> str:
    lines = ["📊 **Kurzstatus**", ""]
    try:
        from outreach import storage, config

        storage.init_db()
        s = storage.stats_summary()
        lines.append(f"Outreach gesamt: {s.get('sent', 0)} versendet, {s.get('queued', 0)} in Queue")
        if config.PROJEKT_ENABLED:
            ps = storage.campaign_stats().get(config.CAMPAIGN_PROJEKT, {})
            lines.append(
                f"Duisburg {config.CAMPAIGN_PROJEKT}: {ps.get('sent', 0)} versendet, "
                f"{ps.get('queued', 0)} Warteschlange"
            )
    except Exception as exc:
        lines.append(f"Outreach: ({exc})")
    try:
        from sheet_client import crm_snapshot

        snap = crm_snapshot()
        leads = snap.get("leads") or []
        hot = sum(1 for l in leads if "Vertrag" in (l.get("stage") or ""))
        lines.append(f"CRM: {len(leads)} Leads, {hot} mit Vertrag-Status")
    except Exception:
        pass
    from crm.mail_inbox import config_status, list_messages as list_mail

    cs = config_status()
    if cs.get("configured"):
        m = list_mail(limit=5)
        lines.append(f"Posteingang: {m.get('unread', 0)} ungelesen / {m.get('total', 0)} gesamt")
    else:
        lines.append("Posteingang: IMAP_PASSWORD in .env fehlt noch")
    return "\n".join(lines)


def _try_auto_reply(user_text: str) -> str | None:
    t = user_text.strip().lower()
    if t in ("status", "stand", "übersicht", "uebersicht", "?"):
        return _auto_status()
    if t in ("help", "hilfe", "befehle"):
        return (
            "**Befehle (sofort):**\n"
            "• `status` — Outreach & CRM\n"
            "• `posteingang` — Mails syncen\n\n"
            "**Alles andere** — ich bearbeite es in Cursor und antworte hier.\n"
            "Beispiele:\n"
            "• Antwort an l.biskup@bki-gruppe.de: Vertrag erhalten, danke\n"
            "• Atakor nachfassen\n"
            "• Was ist im Posteingang?"
        )
    if t in ("posteingang", "inbox", "mails sync", "sync inbox"):
        from crm.mail_inbox import sync_inbox

        r = sync_inbox()
        if not r.get("ok"):
            return f"Posteingang: {r.get('error')}"
        return f"✓ {r.get('new', 0)} neue Mail(s), {r.get('total', 0)} gesamt im Posteingang."

    m = re.match(
        r"^(?:antwort|reply|mail)\s+(?:an\s+)?([^\s:@]+@[^\s:@]+)\s*[:]\s*(.+)$",
        user_text.strip(),
        re.IGNORECASE | re.DOTALL,
    )
    if m:
        from crm.mail_inbox import send_reply

        to_addr = m.group(1).strip().lower()
        body = m.group(2).strip()
        r = send_reply(to_email=to_addr, subject="Kaplan Solutions", body=body)
        if r.get("ok"):
            return f"✓ Mail gesendet an {to_addr}"
        return f"Mail fehlgeschlagen: {r.get('error')}"

    return None


def post_user_message(text: str) -> dict:
    """Nachricht vom Handy — Auto-Antwort oder Warteschlange für Cursor."""
    user_msg = add_message(role="user", text=text, pending_agent=True)
    if not user_msg.get("ok"):
        return user_msg

    auto = _try_auto_reply(text)
    if auto:
        clear_pending(user_msg["id"])
        add_message(role="assistant", text=auto)
        return {"ok": True, "id": user_msg["id"], "auto_replied": True, "reply": auto}

    _notify_admin(text)
    add_message(
        role="assistant",
        text="✓ Empfangen — ich melde mich gleich hier mit der Antwort.",
        meta={"ack_for": user_msg["id"]},
    )
    return {"ok": True, "id": user_msg["id"], "auto_replied": False, "pending": True}


def agent_reply(text: str, *, clear_all_pending: bool = True) -> dict:
    """Antwort vom Cursor-Assistenten (API oder Script)."""
    result = add_message(role="assistant", text=text)
    if clear_all_pending:
        db = _conn()
        db.execute("UPDATE copilot_messages SET pending_agent = 0 WHERE pending_agent = 1")
        db.commit()
        db.close()
    return result
