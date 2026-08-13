"""Eingehende Mails auf zurückgesendete, unterschriebene Verträge prüfen."""

from __future__ import annotations

import email
import imaplib
import json
import os
import re
from datetime import datetime, timedelta
from email.header import decode_header, make_header
from email.utils import parseaddr
from pathlib import Path
from zoneinfo import ZoneInfo

from company_config import company_footer_text
from lead_followup.config import REPLY_EMAIL
from mailer import ADMIN_EMAIL, email_configured, send_email
from sheet_client import crm_snapshot, crm_update

TZ = ZoneInfo("Europe/Berlin")
ROOT = Path(__file__).resolve().parent.parent
SEEN_PATH = ROOT / "data" / "contract_inbox_seen.json"
LOOKBACK_DAYS = int(os.getenv("CONTRACT_INBOX_LOOKBACK_DAYS", "14"))

_BODY_HINT = re.compile(
    r"(unterschrie|signiert|unterzeichnet|gegengezeichnet|vertrag.*(zurück|zurueck|anbei|im anhang)|"
    r"anbei.*vertrag|signed|return.*contract|verbindlich)",
    re.IGNORECASE,
)
_SUBJECT_HINT = re.compile(
    r"(unterschrie|signiert|vertrag|vermittlung|kaplan)",
    re.IGNORECASE,
)
_ATTACH_HINT = re.compile(
    r"(vertrag|vermittlung|contract|kaplan|sign)",
    re.IGNORECASE,
)
_ATTACH_OK = re.compile(r"\.(pdf|html?|png|jpe?g|docx?)$", re.IGNORECASE)
_AUTO_SUBJECT = re.compile(
    r"(automatische? antwort|abwesenh|out of office|autoreply|delivery status|"
    r"undeliverable|unzustellbar|mail delivery failed)",
    re.IGNORECASE,
)
_AUTO_SENDER = re.compile(
    r"(mailer-daemon|postmaster|no-?reply|noreply|bounce|do-?not-?reply)",
    re.IGNORECASE,
)


def configured() -> bool:
    host = os.getenv("IMAP_HOST", "imap.strato.de").strip()
    user = os.getenv("IMAP_USER", os.getenv("REPLY_EMAIL", "")).strip()
    password = os.getenv("IMAP_PASSWORD", "").strip()
    return bool(host and user and password)


def _imap_cfg() -> dict:
    reply = os.getenv("REPLY_EMAIL", "kontakt@kaplan-solutions.de").strip()
    return {
        "host": os.getenv("IMAP_HOST", "imap.strato.de").strip(),
        "port": int(os.getenv("IMAP_PORT", "993")),
        "user": os.getenv("IMAP_USER", reply).strip(),
        "password": os.getenv("IMAP_PASSWORD", ""),
        "folder": os.getenv("IMAP_FOLDER", "INBOX").strip(),
    }


def _decode(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value))).strip()
    except Exception:
        return (value or "").strip()


def _load_seen() -> set[str]:
    if not SEEN_PATH.is_file():
        return set()
    try:
        data = json.loads(SEEN_PATH.read_text(encoding="utf-8"))
        return set(data if isinstance(data, list) else [])
    except (json.JSONDecodeError, OSError):
        return set()


def _save_seen(seen: set[str]) -> None:
    SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    trimmed = sorted(seen)[-5000:]
    SEEN_PATH.write_text(json.dumps(trimmed, ensure_ascii=False, indent=0), encoding="utf-8")


def _body_text(msg: email.message.Message) -> str:
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
        if line.strip().startswith(">"):
            continue
        if re.match(r"^(Am .+ schrieb|Von:|Gesendet:|On .+ wrote:|-{2,}\s*Original)", line.strip()):
            break
        lines.append(line)
    return "\n".join(lines).strip()


def _attachment_names(msg: email.message.Message) -> list[str]:
    names: list[str] = []
    for part in msg.walk():
        fn = part.get_filename()
        if fn:
            names.append(_decode(fn))
    return names


def _is_automatic(msg: email.message.Message, sender: str, subject: str) -> bool:
    if (msg.get("Auto-Submitted") or "").lower().startswith("auto"):
        return True
    if _AUTO_SENDER.search(sender) or _AUTO_SUBJECT.search(subject):
        return True
    return False


def _looks_like_signed_contract(subject: str, body: str, attachments: list[str]) -> bool:
    att_lower = [a.lower() for a in attachments]
    named = [a for a in att_lower if _ATTACH_HINT.search(a) and _ATTACH_OK.search(a)]
    if named:
        return True
    pdfs = [a for a in att_lower if a.endswith(".pdf")]
    if pdfs and (_BODY_HINT.search(body) or _SUBJECT_HINT.search(subject)):
        return True
    if _BODY_HINT.search(body) and (_SUBJECT_HINT.search(subject) or attachments):
        return True
    return False


def _find_lead_by_email(addr: str) -> dict | None:
    addr = (addr or "").strip().lower()
    if not addr:
        return None
    snap = crm_snapshot()
    if not snap.get("ok"):
        return None
    for lead in snap.get("leads") or []:
        if (lead.get("email") or "").strip().lower() == addr:
            return lead
    domain = addr.split("@", 1)[-1]
    for lead in snap.get("leads") or []:
        le = (lead.get("email") or "").strip().lower()
        if le.endswith("@" + domain):
            return lead
    return None


def _notify_admin(*, name: str, company: str, from_email: str, subject: str, ref: str, attachments: list[str]) -> None:
    if not email_configured() or not ADMIN_EMAIL:
        return
    display = name or company or from_email
    subj = f"Kunde hat unterschrieben — {display}"
    att_line = ", ".join(attachments) if attachments else "—"
    text = f"""Kunde hat unterschrieben

{display}
{company}
E-Mail: {from_email}
{f'Anfrage-Nr.: {ref}' if ref else ''}
Betreff der Kundenmail: {subject}
Anhänge: {att_line}

Bitte prüfen Sie das unterschriebene Dokument im Postfach.

{company_footer_text()}
"""
    html = f"""<div style="font-family:Georgia,'Times New Roman',serif;font-size:15px;line-height:1.65;color:#222;max-width:560px">
<p><strong>Kunde hat unterschrieben</strong></p>
<p><strong>{display}</strong><br>{company or '—'}<br><a href="mailto:{from_email}">{from_email}</a></p>
{f'<p>Anfrage-Nr.: {ref}</p>' if ref else ''}
<p>Betreff: {subject}</p>
<p>Anhänge: {att_line}</p>
<p style="color:#555;font-size:14px">Bitte prüfen Sie das unterschriebene Dokument im Postfach.</p>
</div>"""
    send_email(
        ADMIN_EMAIL,
        subj,
        text,
        html,
        reply_to=REPLY_EMAIL,
        mail_kind="transactional",
        entity_ref=ref or "contract-return",
    )


def check_contract_returns(limit: int = 50) -> int:
    """Posteingang prüfen. Gibt Anzahl neu erkannter Vertrags-Rücksendungen zurück."""
    if not configured():
        return 0

    cfg = _imap_cfg()
    seen = _load_seen()
    found = 0

    try:
        imap = imaplib.IMAP4_SSL(cfg["host"], cfg["port"])
        imap.login(cfg["user"], cfg["password"])
        imap.select(cfg["folder"], readonly=True)
    except Exception as exc:
        print(f"[contract-inbox] Postfach nicht erreichbar: {exc}", flush=True)
        return 0

    try:
        since = (datetime.now(TZ) - timedelta(days=LOOKBACK_DAYS)).strftime("%d-%b-%Y")
        status, data = imap.search(None, f"(SINCE {since})")
        if status != "OK":
            return 0
        ids = (data[0] or b"").split()[-limit:]

        for num in ids:
            status, raw = imap.fetch(num, "(BODY.PEEK[])")
            if status != "OK" or not raw or not raw[0]:
                continue
            msg = email.message_from_bytes(raw[0][1])
            message_id = (msg.get("Message-ID") or "").strip()
            if not message_id or message_id in seen:
                continue

            _, sender_email = parseaddr(msg.get("From") or "")
            sender_email = sender_email.strip().lower()
            subject = _decode(msg.get("Subject"))
            if not sender_email or _is_automatic(msg, sender_email, subject):
                seen.add(message_id)
                continue

            body = _body_text(msg)
            attachments = _attachment_names(msg)
            if not _looks_like_signed_contract(subject, body, attachments):
                continue

            seen.add(message_id)
            lead = _find_lead_by_email(sender_email)
            name = (lead.get("name") if lead else "") or sender_email
            company = (lead.get("company") if lead else "") or (lead.get("firma") if lead else "") or ""
            ref = (lead.get("ref") if lead else "") or ""

            if ref:
                crm_update(ref, {
                    "vertrag": "Ja",
                    "stage": "Vertrag unterschrieben",
                    "naechster_schritt": "Unterschriebenen Vertrag prüfen / nächste Schritte",
                    "notiz": (
                        f"Vertrag per E-Mail zurück ({datetime.now(TZ).strftime('%d.%m.%Y %H:%M')}) — "
                        f"{subject}"
                    ),
                })

            _notify_admin(
                name=name,
                company=company,
                from_email=sender_email,
                subject=subject,
                ref=ref,
                attachments=attachments,
            )
            print(
                f"[contract-inbox] Vertrag zurück: {name} <{sender_email}> ref={ref or '—'}",
                flush=True,
            )
            found += 1
    finally:
        try:
            imap.close()
            imap.logout()
        except Exception:
            pass
        _save_seen(seen)

    return found


if __name__ == "__main__":
    n = check_contract_returns()
    print(f"Erkannt: {n} Vertrags-Rücksendung(en)")
