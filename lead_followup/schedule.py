"""Lead-Follow-up am Folgetag planen und versenden — mit Retries & Fallback."""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from lead_followup import config
from lead_followup import storage
from lead_followup.template import build_followup

try:
    from mailer import email_configured, send_email, send_email_scheduled, uses_resend
except ImportError:
    email_configured = lambda: False  # type: ignore
    send_email = None  # type: ignore
    send_email_scheduled = None  # type: ignore
    uses_resend = lambda: False  # type: ignore

TZ = ZoneInfo("Europe/Berlin")
LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "lead_followup.log"
MAX_RETRIES = int(os.getenv("LEAD_FOLLOWUP_RETRIES", "3"))
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "").strip()


def _log(msg: str) -> None:
    line = f"{datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(f"[lead_followup] {msg}", flush=True)
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def next_followup_time(from_dt: datetime | None = None) -> datetime:
    now = from_dt or datetime.now(TZ)
    if now.tzinfo is None:
        now = now.replace(tzinfo=TZ)
    else:
        now = now.astimezone(TZ)
    target_day = now.date() + timedelta(days=1)
    return datetime(
        target_day.year,
        target_day.month,
        target_day.day,
        config.FOLLOWUP_HOUR,
        config.FOLLOWUP_MINUTE,
        0,
        tzinfo=TZ,
    )


def _notify_admin_failure(ref: str, email: str, error: str) -> None:
    if not ADMIN_EMAIL or not email_configured() or not send_email:
        return
    subject = f"[WARNUNG] Lead-Follow-up fehlgeschlagen — {ref}"
    body = (
        f"Follow-up für Lead {ref} ({email}) konnte nicht geplant werden.\n\n"
        f"Fehler: {error}\n\n"
        "Der lokale Daemon oder Cron-Job versucht es erneut. "
        "Bitte prüfen: data/lead_followup.log"
    )
    try:
        send_email(ADMIN_EMAIL, subject, body, f"<pre>{body}</pre>")
    except Exception:
        pass


def _try_resend_schedule(
    email: str,
    subject: str,
    text_body: str,
    html_body: str,
    scheduled: datetime,
) -> str | None:
    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if not send_email_scheduled:
                raise RuntimeError("send_email_scheduled nicht verfügbar")
            resend_id = send_email_scheduled(
                email, subject, text_body, html_body, scheduled
            )
            return resend_id
        except Exception as exc:
            last_exc = exc
            _log(f"Resend-Versuch {attempt}/{MAX_RETRIES} fehlgeschlagen: {exc}")
            if attempt < MAX_RETRIES:
                time.sleep(2 * attempt)
    raise last_exc or RuntimeError("Resend-Planung fehlgeschlagen")


def _ensure_record(data: dict, role_label: str, ref: str) -> tuple[bool, datetime]:
    """Returns (created_new, scheduled_for)."""
    received = datetime.now(TZ)
    scheduled = next_followup_time(received)

    existing = storage.get_by_ref(ref)
    if existing:
        if existing["status"] in ("scheduled", "sent"):
            _log(f"Bereits erledigt: {ref} ({existing['status']})")
            return False, datetime.fromisoformat(existing["scheduled_for"])
        scheduled = datetime.fromisoformat(existing["scheduled_for"])
        storage.reset_to_pending(ref)
        return False, scheduled

    storage.insert_followup(
        ref=ref,
        email=(data.get("email") or "").strip(),
        name=(data.get("name") or "").strip(),
        role=(data.get("role") or "").strip(),
        company=(data.get("company_name") or data.get("company") or "").strip(),
        role_label=role_label,
        received_at=received,
        scheduled_for=scheduled,
    )
    return True, scheduled


def schedule_followup(data: dict, role_label: str) -> bool:
    email = (data.get("email") or "").strip()
    if not email or "@" not in email:
        return False

    ref = (data.get("ref") or "").strip()
    if not ref:
        ref = f"KS-{datetime.now(TZ).strftime('%Y%m%d%H%M%S')}"

    storage.init_db()
    existing = storage.get_by_ref(ref)
    if existing and existing["status"] in ("scheduled", "sent"):
        return True

    _ensure_record({**data, "ref": ref}, role_label, ref)

    if not email_configured():
        _log(f"E-Mail nicht konfiguriert — {ref} in Warteschlange (Daemon/Cron)")
        return False

    subject, text_body, html_body = build_followup({**data, "ref": ref})
    scheduled = datetime.fromisoformat(
        storage.get_by_ref(ref)["scheduled_for"]  # type: ignore[index]
    )

    if uses_resend() and send_email_scheduled:
        try:
            resend_id = _try_resend_schedule(
                email, subject, text_body, html_body, scheduled
            )
            storage.mark_scheduled(ref, resend_id)
            _log(
                f"✓ Geplant {scheduled.strftime('%d.%m.%Y %H:%M')} → {email} ({ref})"
            )
            return True
        except Exception as exc:
            _log(f"Resend endgültig fehlgeschlagen ({ref}) — Fallback aktiv: {exc}")
            _notify_admin_failure(ref, email, str(exc))
            # pending lassen — process_due sendet um 8 Uhr direkt
            return False

    _log(f"Warteschlange bis {scheduled.strftime('%d.%m.%Y %H:%M')} → {email} ({ref})")
    return True


def send_followup_row(row) -> bool:
    data = {
        "ref": row["ref"],
        "email": row["email"],
        "name": row["name"],
        "role": row["role"],
        "company": row["company"],
    }
    subject, text_body, html_body = build_followup(data)
    try:
        send_email(  # type: ignore
            row["email"],
            subject,
            text_body,
            html_body,
            reply_to=config.REPLY_EMAIL,
        )
        storage.mark_sent(row["ref"])
        _log(f"✓ Fallback gesendet an {row['email']} ({row['ref']})")
        return True
    except Exception as exc:
        storage.mark_failed(row["ref"], str(exc))
        _notify_admin_failure(row["ref"], row["email"], str(exc))
        _log(f"✗ Versand fehlgeschlagen {row['ref']}: {exc}")
        return False


def retry_unscheduled() -> int:
    """Versucht Resend-Planung für pending ohne resend_id."""
    if not uses_resend() or not email_configured():
        return 0
    storage.init_db()
    count = 0
    for row in storage.pending_without_resend():
        data = {
            "ref": row["ref"],
            "email": row["email"],
            "name": row["name"],
            "role": row["role"],
            "company": row["company"],
        }
        subject, text_body, html_body = build_followup(data)
        scheduled = datetime.fromisoformat(row["scheduled_for"])
        if scheduled.tzinfo is None:
            scheduled = scheduled.replace(tzinfo=TZ)
        try:
            resend_id = _try_resend_schedule(
                row["email"], subject, text_body, html_body, scheduled
            )
            storage.mark_scheduled(row["ref"], resend_id)
            _log(f"✓ Nachgeplant → {row['email']} ({row['ref']})")
            count += 1
        except Exception as exc:
            _log(f"Nachplanung fehlgeschlagen {row['ref']}: {exc}")
    return count


def process_due() -> int:
    if not email_configured():
        return 0
    storage.init_db()
    retry_unscheduled()
    sent = 0
    for row in storage.due_pending():
        if send_followup_row(row):
            sent += 1
    return sent
