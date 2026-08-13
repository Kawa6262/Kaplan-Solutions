"""Antworten von angeschriebenen Firmen erkennen, ins CRM schreiben und melden.

Liest das Antwortpostfach per IMAP mit BODY.PEEK — der Gelesen-Status im
Postfach bleibt unangetastet, damit nichts an der manuellen Bearbeitung
vorbeiläuft. Bereits verarbeitete Nachrichten stehen in der Tabelle 'replies'.
"""

from __future__ import annotations

import email
import imaplib
import os
import re
import sys
from datetime import datetime, timedelta
from email.header import decode_header, make_header
from email.utils import parseaddr
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sheet_client import crm_update

from outreach import config
from outreach import storage
from outreach.projekt import AKTUELL

TZ = ZoneInfo("Europe/Berlin")

# Partner-Stufe im CRM, sobald eine Firma sich meldet.
REPLY_STAGE = os.getenv("OUTREACH_REPLY_STAGE", "Erstgespräch geplant")
LOOKBACK_DAYS = int(os.getenv("OUTREACH_REPLY_LOOKBACK_DAYS", "7"))

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


def _cfg() -> dict:
    reply_addr = os.getenv("REPLY_EMAIL", "kontakt@kaplan-solutions.de").strip()
    return {
        "host": os.getenv("IMAP_HOST", "imap.strato.de").strip(),
        "port": int(os.getenv("IMAP_PORT", "993")),
        "user": os.getenv("IMAP_USER", reply_addr).strip(),
        "password": os.getenv("IMAP_PASSWORD", ""),
        "folder": os.getenv("IMAP_FOLDER", "INBOX").strip(),
    }


def configured() -> bool:
    c = _cfg()
    return bool(c["host"] and c["user"] and c["password"])


def _decode(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value))).strip()
    except Exception:
        return value.strip()


def _body_text(msg: email.message.Message) -> str:
    """Nur der neue Text — zitierte Passagen und Signatur interessieren nicht."""
    raw = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.get_filename():
                try:
                    raw = part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="replace"
                    )
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
        stripped = line.strip()
        if stripped.startswith(">"):
            continue
        if re.match(r"^(Am .+ schrieb|Von:|Gesendet:|On .+ wrote:|-{2,}\s*Original)", stripped):
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
    if _AUTO_SENDER.search(sender) or _AUTO_SUBJECT.search(subject):
        return True
    return False


def _push_to_crm(row, subject: str, snippet: str) -> str:
    """Sheet-Eintrag sicherstellen und die Pipeline-Stufe hochsetzen."""
    from outreach import sheet_sync

    ref = ""
    try:
        ref = (row["sheet_ref"] or "").strip()
    except (IndexError, KeyError):
        ref = ""

    if not ref or ref in ("n/a", "duplicate"):
        try:
            sheet_sync.sync_prospect(row)
            fresh = storage.get_prospect(int(row["id"]))
            ref = (fresh["sheet_ref"] or "").strip() if fresh else ""
        except Exception as exc:
            print(f"[outreach] Sheet-Eintrag fehlgeschlagen: {exc}", flush=True)

    if not ref or ref in ("n/a", "duplicate"):
        return ""

    campaign = (row["campaign"] or "").strip()
    quelle = (
        f"Projekt-Ausschreibung {AKTUELL.referenz}"
        if campaign == config.CAMPAIGN_PROJEKT
        else "Outreach"
    )
    notiz = f"Antwort am {datetime.now(TZ).strftime('%d.%m.%Y %H:%M')} — {subject}\n{snippet[:600]}"
    result = crm_update(
        ref,
        {
            "stage": REPLY_STAGE,
            "quelle": quelle,
            "nachster_schritt": "Rückruf und Ortstermin abstimmen",
            "notiz": notiz,
        },
    )
    if not result.get("ok"):
        print(f"[outreach] CRM-Update {ref} fehlgeschlagen: {result.get('error')}", flush=True)
    return ref


def _alert(row, from_email: str, subject: str, snippet: str, ref: str) -> None:
    try:
        from mailer import email_configured, send_email
    except ImportError:
        return
    admin = os.getenv("OUTREACH_ALERT_EMAIL", os.getenv("ADMIN_EMAIL", "")).strip()
    if not admin or not email_configured():
        return

    company = row["company_name"] if row else from_email
    city = row["city"] if row else ""
    trade = row["trade"] if row else ""
    phone = (row["phone"] if row else "") or "—"

    text = f"""Eine Firma hat auf die Ausschreibung geantwortet.

{company}
{trade} · {city}
E-Mail: {from_email}
Telefon: {phone}
CRM: {ref or 'kein Eintrag'}

Betreff: {subject}

{snippet[:1200]}

Im CRM steht der Vorgang jetzt auf "{REPLY_STAGE}".
"""
    html = f"""<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#1a1a1a;line-height:1.6;max-width:600px">
<div style="background:#0b3d2e;color:#fff;padding:16px 20px;border-radius:8px 8px 0 0">
  <p style="margin:0;font-size:18px;font-weight:700">Antwort auf die Ausschreibung</p>
</div>
<div style="border:1px solid #e0e0e0;border-top:none;border-radius:0 0 8px 8px;padding:20px">
  <p style="margin:0 0 4px;font-size:20px;font-weight:700">{company}</p>
  <p style="margin:0 0 16px;color:#666">{trade} · {city}</p>
  <table style="width:100%;border-collapse:collapse;margin-bottom:16px">
    <tr><td style="padding:6px 0;color:#666">E-Mail</td><td style="padding:6px 0"><a href="mailto:{from_email}">{from_email}</a></td></tr>
    <tr><td style="padding:6px 0;color:#666">Telefon</td><td style="padding:6px 0">{phone}</td></tr>
    <tr><td style="padding:6px 0;color:#666">CRM</td><td style="padding:6px 0">{ref or 'kein Eintrag'}</td></tr>
  </table>
  <p style="margin:0 0 6px;font-weight:700">{subject}</p>
  <div style="background:#f6f6f6;border-radius:6px;padding:14px;white-space:pre-wrap">{snippet[:1200]}</div>
  <p style="margin:16px 0 0;color:#666;font-size:13px">Im CRM auf „{REPLY_STAGE}" gesetzt.</p>
</div>
</body></html>"""
    try:
        send_email(admin, f"Antwort: {company} ({city})", text, html)
    except Exception as exc:
        print(f"[outreach] Antwort-Benachrichtigung fehlgeschlagen: {exc}", flush=True)


def check_replies(limit: int = 40) -> int:
    """Neue Antworten verarbeiten. Returns Anzahl erkannter Firmenantworten."""
    if not configured():
        return 0

    c = _cfg()
    try:
        imap = imaplib.IMAP4_SSL(c["host"], c["port"])
        imap.login(c["user"], c["password"])
        imap.select(c["folder"], readonly=True)
    except Exception as exc:
        print(f"[outreach] Postfach nicht erreichbar: {exc}", flush=True)
        return 0

    found = 0
    try:
        since = (datetime.now(TZ) - timedelta(days=LOOKBACK_DAYS)).strftime("%d-%b-%Y")
        status, data = imap.search(None, f'(SINCE {since})')
        if status != "OK":
            return 0
        ids = (data[0] or b"").split()[-limit:]

        for num in ids:
            status, raw = imap.fetch(num, "(BODY.PEEK[])")
            if status != "OK" or not raw or not raw[0]:
                continue
            msg = email.message_from_bytes(raw[0][1])

            message_id = (msg.get("Message-ID") or "").strip()
            if not message_id or storage.reply_seen(message_id):
                continue

            sender_name, sender_email = parseaddr(msg.get("From") or "")
            sender_email = sender_email.strip().lower()
            subject = _decode(msg.get("Subject"))
            if not sender_email or _is_automatic(msg, sender_email, subject):
                continue

            row = storage.find_sent_prospect_by_email(sender_email)
            if not row:
                continue

            snippet = _body_text(msg)
            ref = _push_to_crm(row, subject, snippet)
            storage.record_reply(
                message_id=message_id,
                prospect_id=int(row["id"]),
                from_email=sender_email,
                company_name=row["company_name"],
                subject=subject,
                snippet=snippet[:2000],
                crm_ref=ref,
            )
            _alert(row, sender_email, subject, snippet, ref)
            print(
                f"[outreach] Antwort: {row['company_name']} <{sender_email}> → CRM {ref or '—'}",
                flush=True,
            )
            found += 1
    finally:
        try:
            imap.close()
            imap.logout()
        except Exception:
            pass

    return found
