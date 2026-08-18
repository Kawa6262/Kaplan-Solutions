"""Assistent-Chat in Kaplan Sales — intelligente Befehle vom Handy."""

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
    lines = ["📊 Kurzstatus", ""]
    try:
        from outreach import storage, config

        storage.init_db()
        s = storage.stats_summary()
        lines.append(f"• Outreach: {s.get('sent', 0)} versendet, {s.get('queued', 0)} in Warteschlange")
        if config.PROJEKT_ENABLED:
            ps = storage.campaign_stats().get(config.CAMPAIGN_PROJEKT, {})
            lines.append(
                f"• Duisburg {config.CAMPAIGN_PROJEKT}: {ps.get('sent', 0)} versendet, "
                f"{ps.get('queued', 0)} wartend"
            )
    except Exception as exc:
        lines.append(f"• Outreach: ({exc})")
    try:
        from sheet_client import crm_snapshot

        snap = crm_snapshot()
        leads = snap.get("leads") or []
        hot = [l for l in leads if "Vertrag" in (l.get("stage") or "")]
        lines.append(f"• CRM: {len(leads)} Leads, {len(hot)} mit Vertrag-Status")
        if hot[:3]:
            lines.append("  Top Vertrag:")
            for l in hot[:3]:
                lines.append(f"  – {l.get('ref')} {l.get('name') or l.get('company')} ({l.get('stage')})")
    except Exception:
        lines.append("• CRM: Sheet nicht erreichbar")
    try:
        from crm.mail_inbox import config_status, list_messages as list_mail

        cs = config_status()
        if cs.get("configured"):
            m = list_mail(limit=3)
            lines.append(f"• Posteingang: {m.get('unread', 0)} ungelesen / {m.get('total', 0)} gesamt")
            for msg in m.get("messages") or []:
                lines.append(f"  – {msg.get('from_email')}: {(msg.get('subject') or '')[:40]}")
        else:
            lines.append("• Posteingang: nicht konfiguriert")
    except Exception:
        pass
    return "\n".join(lines)


def _try_auto_reply(user_text: str) -> str | None:
    t = user_text.strip().lower()
    if t in ("status", "stand", "übersicht", "uebersicht", "?"):
        return _auto_status()
    if t in ("help", "hilfe", "befehle", "help"):
        return (
            "Ich bin dein Kaplan Sales Assistent.\n\n"
            "Sofort-Befehle:\n"
            "• status — Zahlen & Überblick\n"
            "• posteingang — Mails syncen & anzeigen\n"
            "• hot leads — wichtige Kontakte\n"
            "• Schick mir eine Test-Mail — an deine Gmail\n\n"
            "Oder frei schreiben, z. B.:\n"
            "• Was steht im Posteingang?\n"
            "• Antwort an l.biskup@bki-gruppe.de: Vertrag erhalten\n"
            "• Wie läuft Duisburg Outreach?"
        )
    if t in ("posteingang", "inbox", "mails sync", "sync inbox", "posteingang sync"):
        return _inbox_report(sync=True)

    if t in ("hot leads", "heisse leads", "heiss leads", "vertrag", "pipeline"):
        from sheet_client import crm_snapshot

        snap = crm_snapshot()
        leads = snap.get("leads") or []
        hot = [l for l in leads if "Vertrag" in (l.get("stage") or "")]
        if not hot:
            return "Keine Leads mit Vertrag-Status gefunden."
        lines = ["🔥 Vertrag / heiße Leads:", ""]
        for l in hot[:10]:
            lines.append(
                f"• {l.get('ref')} — {l.get('name') or l.get('company')} "
                f"({l.get('stage')}) {l.get('email') or ''}"
            )
        return "\n".join(lines)

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

    if _wants_test_mail(user_text):
        return _send_test_mail()

    return None


def _wants_test_mail(text: str) -> bool:
    tl = text.lower()
    if re.search(r"(test\s*mail|testmail|test\s*-?\s*mail|testmail)", tl):
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
            "und werden automatisch an diese Gmail weitergeleitet."
        )
        send_email(admin, subj, body, f"<p>{body}</p>", mail_kind="transactional")
        return f"✓ Test-Mail gesendet an {admin}. Schau in dein Postfach (ggf. Spam)."
    except Exception as exc:
        return f"Test-Mail fehlgeschlagen: {exc}"


def _inbox_report(*, sync: bool = True) -> str:
    from crm.mail_inbox import list_messages, sync_inbox

    if sync:
        r = sync_inbox()
        if not r.get("ok"):
            return f"Posteingang: {r.get('error')}"
    m = list_messages(limit=8)
    if not m.get("messages"):
        return "Posteingang ist leer — noch keine Mails bei kontakt@kaplan-solutions.de."
    lines = [f"📥 {m.get('unread', 0)} ungelesen / {m.get('total', 0)} gesamt", ""]
    for msg in m.get("messages") or []:
        lines.append(f"• {msg.get('from_email')}: {msg.get('subject') or '—'}")
        if msg.get("analysis_summary"):
            lines.append(f"  🤖 {msg.get('analysis_summary')}")
        else:
            preview = (msg.get("body") or "")[:100]
            if preview:
                lines.append(f"  {preview}…")
    return "\n".join(lines)


def _smart_fallback(user_text: str) -> str:
    """Antwort ohne KI — nur kurze Befehle, keine langen Fragen abfangen."""
    tl = user_text.strip().lower()
    short = len(tl) < 70

    if _wants_test_mail(user_text):
        return _send_test_mail()

    if short and tl in ("status", "stand", "übersicht", "uebersicht", "?"):
        return _auto_status()
    if short and any(w in tl for w in ("posteingang", "inbox", "postfach")) and "?" not in tl[20:]:
        return _inbox_report(sync=True)
    if short and tl.startswith("hot"):
        from sheet_client import crm_snapshot

        snap = crm_snapshot()
        leads = snap.get("leads") or []
        hot = [l for l in leads if "Vertrag" in (l.get("stage") or "")]
        if not hot:
            return "Keine Leads mit Vertrag-Status gefunden."
        lines = ["🔥 Vertrag / heiße Leads:", ""]
        for l in hot[:10]:
            lines.append(
                f"• {l.get('ref')} — {l.get('name') or l.get('company')} "
                f"({l.get('stage')}) {l.get('email') or ''}"
            )
        return "\n".join(lines)
    if short and any(w in tl for w in ("lead", "kontakt", "vertrag", "bki", "atakor")):
        from sheet_client import crm_snapshot

        snap = crm_snapshot()
        q = user_text.lower()
        hits = [
            l
            for l in (snap.get("leads") or [])
            if q in (l.get("name") or "").lower()
            or q in (l.get("company") or "").lower()
            or q in (l.get("email") or "").lower()
            or q in (l.get("ref") or "").lower()
        ]
        if hits:
            l = hits[0]
            return (
                f"{l.get('ref')} — {l.get('name') or l.get('company')}\n"
                f"Stage: {l.get('stage')}\n"
                f"E-Mail: {l.get('email') or '—'}\n"
                f"Projekt: {l.get('project') or '—'}"
            )
        return _auto_status()
    try:
        from crm import copilot_ai

        if not copilot_ai.configured():
            return (
                "KI-Assistent ist auf dem Server noch nicht konfiguriert.\n\n"
                "Render → Environment → GEMINI_API_KEY + COPILOT_PROVIDER=gemini setzen.\n\n"
                f"{_auto_status()}\n\n"
                "Kurzbefehle: status · posteingang · hot leads"
            )
    except Exception:
        pass
    return (
        f"Verstanden: „{user_text[:200]}“\n\n"
        f"{_auto_status()}\n\n"
        "Tipp: status · posteingang · hot leads — oder konkret fragen."
    )


def post_user_message(text: str) -> dict:
    user_msg = add_message(role="user", text=text, pending_agent=True)
    if not user_msg.get("ok"):
        return user_msg

    reply_text = _try_auto_reply(text)
    ai_note = ""

    if not reply_text:
        try:
            from crm import copilot_ai

            if copilot_ai.configured():
                ai_reply = copilot_ai.reply(text, _chat_history())
                if ai_reply:
                    reply_text = ai_reply
                elif copilot_ai.quota_exhausted():
                    pname = copilot_ai.provider_name() or "KI"
                    ai_note = (
                        f"\n\n(Hinweis: {pname}-Limit erreicht — später erneut versuchen. "
                        "Bis dahin: status · posteingang · hot leads.)"
                    )
                elif copilot_ai.last_error():
                    ai_note = f"\n\n(KI-Hinweis: {copilot_ai.last_error()[:200]})"
        except Exception:
            reply_text = None

    if not reply_text:
        reply_text = _smart_fallback(text)

    if ai_note and ai_note not in reply_text:
        reply_text = reply_text + ai_note

    clear_pending(user_msg["id"])
    add_message(role="assistant", text=reply_text)
    return {
        "ok": True,
        "id": user_msg["id"],
        "auto_replied": True,
        "reply": reply_text,
        "pending": False,
    }


def agent_reply(text: str, *, clear_all_pending: bool = True) -> dict:
    result = add_message(role="assistant", text=text)
    if clear_all_pending:
        clear_pending()
    return result
