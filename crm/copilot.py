"""Assistent-Chat in Kaplan Sales — regelbasiert (0 €) + optional KI."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

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


def clear_pending(user_message_id: str | None = None) -> None:
    db = _conn()
    if user_message_id:
        db.execute("UPDATE copilot_messages SET pending_agent = 0 WHERE id = ?", (user_message_id,))
    else:
        db.execute("UPDATE copilot_messages SET pending_agent = 0 WHERE pending_agent = 1")
    db.commit()
    db.close()


def _chat_history(limit: int = 12) -> list[dict]:
    db = _conn()
    rows = db.execute(
        "SELECT role, text FROM copilot_messages ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    db.close()
    return [dict(r) for r in reversed(rows)]


def _auto_status() -> str:
    from crm import copilot_rules

    return copilot_rules._cmd_status("status", copilot_rules._snapshot()) or "Status nicht verfügbar."


def _wants_test_mail(text: str) -> bool:
    tl = text.lower()
    if re.search(r"(test\s*mail|testmail|test\s*-?\s*mail)", tl):
        return bool(re.search(r"(schick|sende|send|schicken|mir|mal|eine|bitte|kannst|könntest)", tl))
    return bool(re.search(r"(schick|sende).{0,30}(mail|e-mail|email)", tl))


def _send_test_mail() -> str:
    admin = os.getenv("ADMIN_EMAIL", "").strip()
    if not admin:
        return "ADMIN_EMAIL fehlt — kann keine Test-Mail senden."
    try:
        from mailer import email_configured, send_email

        if not email_configured():
            return "E-Mail-Versand ist nicht konfiguriert."
        subj = "Kaplan Sales — Test-Mail vom Assistenten"
        body = (
            "Das ist eine Test-Mail von deinem Kaplan Sales Assistenten.\n\n"
            "Eingehende Mails an kontakt@kaplan-solutions.de landen im CRM Posteingang "
            "und werden automatisch an deine Gmail weitergeleitet."
        )
        send_email(admin, subj, body, f"<p>{body}</p>", mail_kind="transactional")
        return f"✓ Test-Mail gesendet an {admin}. Schau in dein Postfach (ggf. Spam)."
    except Exception as exc:
        return f"Test-Mail fehlgeschlagen: {exc}"


def _inbox_report(*, sync: bool = True) -> str:
    from crm import copilot_rules

    return copilot_rules._cmd_inbox("posteingang", copilot_rules._snapshot()) or "Posteingang nicht verfügbar."


def post_user_message(text: str) -> dict:
    from crm import copilot_rules

    user_msg = add_message(role="user", text=text, pending_agent=True)
    if not user_msg.get("ok"):
        return user_msg

    reply_text = copilot_rules.handle(text)

    if copilot_rules.ai_enabled() and reply_text and reply_text.startswith("Das habe ich nicht eindeutig"):
        try:
            from crm import copilot_ai

            if copilot_ai.configured():
                ai_reply = copilot_ai.reply(text, _chat_history())
                if ai_reply:
                    reply_text = ai_reply
                elif copilot_ai.last_error():
                    reply_text = f"{reply_text}\n\n(KI optional: {copilot_ai.last_error()[:150]})"
        except Exception:
            pass

    clear_pending(user_msg["id"])
    add_message(role="assistant", text=reply_text)
    return {
        "ok": True,
        "id": user_msg["id"],
        "auto_replied": True,
        "reply": reply_text,
        "pending": False,
        "mode": "ai" if copilot_rules.ai_enabled() else "rules",
    }


def agent_reply(text: str, *, clear_all_pending: bool = True) -> dict:
    result = add_message(role="assistant", text=text)
    if clear_all_pending:
        clear_pending()
    return result
