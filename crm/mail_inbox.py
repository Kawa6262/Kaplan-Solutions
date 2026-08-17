"""Posteingang kontakt@ per IMAP — für Kaplan Sales + Assistent."""

from __future__ import annotations

import email
import imaplib
import os
import re
import sqlite3
from datetime import datetime, timedelta
from email.header import decode_header, make_header
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "crm_comms.db"
TZ = ZoneInfo("Europe/Berlin")
LOOKBACK_DAYS = int(os.getenv("IMAP_LOOKBACK_DAYS", "21"))

_AUTO_SUBJECT = re.compile(
    r"(automatische? antwort|abwesenh|out of office|autoreply|auto-reply|"
    r"urlaub|nicht im haus|delivery status|undeliverable|unzustellbar|"
    r"mail delivery failed|returned mail)",
    re.IGNORECASE,
)
_AUTO_SENDER = re.compile(
    r"(mailer-daemon|postmaster|no-?reply|noreply|bounce|do-?not-?reply|resend)",
    re.IGNORECASE,
)


def _cfg() -> dict:
    reply = os.getenv("REPLY_EMAIL", "kontakt@kaplan-solutions.de").strip()
    return {
        "host": os.getenv("IMAP_HOST", "imap.strato.de").strip(),
        "port": int(os.getenv("IMAP_PORT", "993")),
        "user": os.getenv("IMAP_USER", reply).strip(),
        "password": os.getenv("IMAP_PASSWORD", "").strip(),
        "folder": os.getenv("IMAP_FOLDER", "INBOX").strip(),
    }


def configured() -> bool:
    c = _cfg()
    if c["host"] and c["user"] and c["password"]:
        return True
    try:
        from crm import resend_inbox

        return resend_inbox.configured()
    except Exception:
        return False


def config_status() -> dict:
    c = _cfg()
    imap_ok = bool(c["host"] and c["user"] and c["password"])
    status = {
        "configured": configured(),
        "imap_configured": imap_ok,
        "host": c["host"],
        "user": c["user"],
        "folder": c["folder"],
        "password_set": bool(c["password"]),
    }
    try:
        from crm import resend_inbox

        status["resend_inbound"] = resend_inbox.configured()
    except Exception:
        status["resend_inbound"] = False
    return status


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS inbox_messages (
            message_id TEXT PRIMARY KEY,
            from_email TEXT NOT NULL,
            from_name TEXT,
            subject TEXT,
            body TEXT,
            received_at TEXT NOT NULL,
            synced_at TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            crm_ref TEXT,
            in_reply_to TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_inbox_received ON inbox_messages(received_at DESC);
        CREATE INDEX IF NOT EXISTS idx_inbox_from ON inbox_messages(from_email);
        """
    )
    for col, typ in (
        ("analysis_summary", "TEXT"),
        ("analysis_intent", "TEXT"),
        ("analysis_priority", "TEXT"),
    ):
        try:
            db.execute(f"ALTER TABLE inbox_messages ADD COLUMN {col} {typ}")
        except sqlite3.OperationalError:
            pass
    return db


def save_analysis(message_id: str, analysis: dict) -> None:
    db = _conn()
    db.execute(
        """
        UPDATE inbox_messages SET
            analysis_summary = ?,
            analysis_intent = ?,
            analysis_priority = ?
        WHERE message_id = ?
        """,
        (
            (analysis.get("summary") or "")[:2000],
            analysis.get("intent") or "",
            analysis.get("priority") or "normal",
            message_id,
        ),
    )
    db.commit()
    db.close()


def _decode(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value))).strip()
    except Exception:
        return (value or "").strip()


def _body_text(msg: email.message.Message) -> str:
    raw = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain" and not part.get_filename():
                try:
                    raw = part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="replace"
                    )
                    break
                except Exception:
                    continue
        if not raw:
            for part in msg.walk():
                if part.get_content_type() == "text/html" and not part.get_filename():
                    try:
                        raw = part.get_payload(decode=True).decode(
                            part.get_content_charset() or "utf-8", errors="replace"
                        )
                        raw = re.sub(r"<[^>]+>", " ", raw)
                        break
                    except Exception:
                        continue
    else:
        try:
            raw = msg.get_payload(decode=True).decode(
                msg.get_content_charset() or "utf-8", errors="replace"
            )
        except Exception:
            raw = str(msg.get_payload())
    lines: list[str] = []
    for line in raw.splitlines():
        if line.strip().startswith(">"):
            continue
        if re.match(r"^(Am .+ schrieb|Von:|Gesendet:|On .+ wrote:|-{2,}\s*Original)", line.strip()):
            break
        lines.append(line)
    return "\n".join(lines).strip()


def _is_automatic(msg: email.message.Message, sender: str, subject: str) -> bool:
    if (msg.get("Auto-Submitted") or "").lower().startswith("auto"):
        return True
    if msg.get("X-Autoreply") or msg.get("X-Autorespond"):
        return True
    if (msg.get("Precedence") or "").lower() in ("bulk", "auto_reply", "junk"):
        return True
    return bool(_AUTO_SENDER.search(sender) or _AUTO_SUBJECT.search(subject))


def _parse_date(msg: email.message.Message) -> str:
    raw = msg.get("Date")
    try:
        if raw:
            dt = parsedate_to_datetime(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=TZ)
            return dt.astimezone(TZ).isoformat(timespec="seconds")
    except Exception:
        pass
    return datetime.now(TZ).isoformat(timespec="seconds")


def _guess_crm_ref(subject: str, body: str) -> str:
    m = re.search(r"KS-\d{4}-[\w-]+", f"{subject}\n{body}", re.IGNORECASE)
    return m.group(0).upper() if m else ""


def sync_inbox(limit: int = 60) -> dict:
    resend_result: dict | None = None
    try:
        from crm import resend_inbox

        if resend_inbox.configured():
            resend_result = resend_inbox.sync_resend_inbox(limit=limit)
    except Exception as exc:
        resend_result = {"ok": False, "error": str(exc)[:120]}

    c = _cfg()
    imap_ok = bool(c["host"] and c["user"] and c["password"])
    if not imap_ok:
        if resend_result and resend_result.get("ok"):
            _after_sync_hooks(limit)
            return {**resend_result, **config_status(), "source": "resend"}
        err = (resend_result or {}).get("error") or "Postfach nicht konfiguriert"
        return {"ok": False, "error": err, **config_status()}

    db = _conn()
    new_count = 0
    total = 0
    try:
        imap = imaplib.IMAP4_SSL(c["host"], c["port"])
        imap.login(c["user"], c["password"])
        imap.select(c["folder"], readonly=True)
    except Exception as exc:
        db.close()
        if resend_result and resend_result.get("ok"):
            _after_sync_hooks(limit)
            return {
                **resend_result,
                **config_status(),
                "source": "resend",
                "imap_skipped": str(exc)[:80],
            }
        return {"ok": False, "error": f"Postfach nicht erreichbar: {exc}", **config_status()}

    now = datetime.now(TZ).isoformat(timespec="seconds")
    try:
        since = (datetime.now(TZ) - timedelta(days=LOOKBACK_DAYS)).strftime("%d-%b-%Y")
        status, data = imap.search(None, f"(SINCE {since})")
        if status != "OK":
            total = db.execute("SELECT COUNT(*) FROM inbox_messages").fetchone()[0]
            db.close()
            return {"ok": True, "new": 0, "total": total, **config_status()}
        ids = (data[0] or b"").split()[-limit:]

        for num in ids:
            status, raw = imap.fetch(num, "(BODY.PEEK[])")
            if status != "OK" or not raw or not raw[0]:
                continue
            msg = email.message_from_bytes(raw[0][1])
            message_id = (msg.get("Message-ID") or f"uid-{num.decode()}").strip()
            sender_name, sender_email = parseaddr(msg.get("From") or "")
            sender_email = sender_email.strip().lower()
            subject = _decode(msg.get("Subject"))
            if not sender_email or _is_automatic(msg, sender_email, subject):
                continue

            body = _body_text(msg)
            received = _parse_date(msg)
            crm_ref = _guess_crm_ref(subject, body)
            try:
                cur = db.execute(
                    """
                    INSERT OR IGNORE INTO inbox_messages
                    (message_id, from_email, from_name, subject, body, received_at, synced_at, crm_ref, in_reply_to)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        message_id,
                        sender_email,
                        sender_name,
                        subject,
                        body[:8000],
                        received,
                        now,
                        crm_ref or None,
                        (msg.get("In-Reply-To") or "")[:200] or None,
                    ),
                )
                if cur.rowcount:
                    new_count += 1
            except sqlite3.Error:
                pass
        db.commit()
    finally:
        try:
            imap.close()
            imap.logout()
        except Exception:
            pass
        total = db.execute("SELECT COUNT(*) FROM inbox_messages").fetchone()[0]
        db.close()

    _after_sync_hooks(limit)
    out = {"ok": True, "new": new_count, "total": total, **config_status(), "source": "imap"}
    if resend_result and resend_result.get("ok"):
        out["resend_new"] = resend_result.get("new", 0)
    return out


def _after_sync_hooks(limit: int) -> None:
    _process_unanalyzed(limit=min(limit, 15))
    try:
        from outreach import storage as outreach_storage

        outreach_storage.init_db()
        from outreach import replies

        if replies.configured():
            replies.check_replies(limit=limit)
    except Exception:
        pass


def _process_unanalyzed(limit: int = 10) -> None:
    db = _conn()
    rows = db.execute(
        """
        SELECT message_id, from_email, from_name, subject, body
        FROM inbox_messages
        WHERE COALESCE(analysis_summary, '') = ''
        ORDER BY received_at DESC LIMIT ?
        """,
        (limit,),
    ).fetchall()
    db.close()
    for row in rows:
        try:
            from crm.inbox_analyzer import process_inbound

            process_inbound(
                message_id=row["message_id"],
                from_email=row["from_email"],
                from_name=row["from_name"] or "",
                subject=row["subject"] or "",
                body=row["body"] or "",
                notify=False,
            )
        except Exception as exc:
            print(f"[inbox] Analyse fehlgeschlagen ({row['message_id']}): {exc}", flush=True)


def list_messages(*, limit: int = 40, offset: int = 0, unread_only: bool = False) -> dict:
    db = _conn()
    where = "WHERE is_read = 0" if unread_only else ""
    rows = db.execute(
        f"""
        SELECT message_id, from_email, from_name, subject, body, received_at, is_read, crm_ref,
               analysis_summary, analysis_intent, analysis_priority
        FROM inbox_messages {where}
        ORDER BY received_at DESC LIMIT ? OFFSET ?
        """,
        (limit, offset),
    ).fetchall()
    unread = db.execute("SELECT COUNT(*) FROM inbox_messages WHERE is_read = 0").fetchone()[0]
    total = db.execute("SELECT COUNT(*) FROM inbox_messages").fetchone()[0]
    db.close()
    return {
        "ok": True,
        "messages": [dict(r) for r in rows],
        "unread": unread,
        "total": total,
        **config_status(),
    }


def mark_read(message_id: str, read: bool = True) -> dict:
    db = _conn()
    db.execute(
        "UPDATE inbox_messages SET is_read = ? WHERE message_id = ?",
        (1 if read else 0, message_id),
    )
    db.commit()
    db.close()
    return {"ok": True}


def send_reply(*, to_email: str, subject: str, body: str, reply_to_message_id: str | None = None) -> dict:
    from mailer import email_configured, send_email
    from lead_followup.config import REPLY_EMAIL

    to_email = (to_email or "").strip()
    if not to_email or "@" not in to_email:
        return {"ok": False, "error": "Ungültige E-Mail"}
    if not email_configured():
        return {"ok": False, "error": "E-Mail-Versand nicht konfiguriert"}

    subj = (subject or "").strip()
    if subj and not subj.lower().startswith("re:"):
        subj = f"Re: {subj}"

    send_email(
        to_email,
        subj or "Kaplan Solutions",
        body,
        f"<div style='font-family:Georgia,serif;font-size:15px;line-height:1.6;white-space:pre-wrap'>{body}</div>",
        reply_to=REPLY_EMAIL,
        mail_kind="transactional",
    )
    if reply_to_message_id:
        mark_read(reply_to_message_id, True)
    return {"ok": True, "to": to_email, "subject": subj}


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    print("IMAP:", config_status())
    r = sync_inbox(limit=30)
    print("Sync:", r)
