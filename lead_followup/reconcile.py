"""Nachhol-Logik: Leads aus Inbox-JSONs sicherstellen."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from lead_followup import storage
from lead_followup.schedule import schedule_followup

ROLE_LABELS = {
    "bauherr": "Auftraggeber (Bauherr)",
    "unternehmen": "Auftragnehmer (Unternehmen)",
}

TZ = ZoneInfo("Europe/Berlin")


def _inbox_dir() -> Path:
    root = Path(__file__).resolve().parent.parent
    return root / "data" / "inbox"


def scan_inbox(limit_days: int = 14) -> dict:
    """Plant fehlende Follow-ups für gespeicherte Anfragen."""
    storage.init_db()
    inbox = _inbox_dir()
    if not inbox.is_dir():
        return {"scanned": 0, "scheduled": 0, "skipped": 0}

    cutoff = datetime.now(TZ).timestamp() - limit_days * 86400
    scheduled = 0
    skipped = 0
    scanned = 0

    for path in sorted(inbox.glob("*.json")):
        try:
            if path.stat().st_mtime < cutoff:
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                continue
            scanned += 1
            ref = (payload.get("ref") or "").strip()
            if ref:
                existing = storage.get_by_ref(ref)
                if existing and existing["status"] in ("scheduled", "sent"):
                    skipped += 1
                    continue
            role = (payload.get("role") or "").strip()
            role_label = payload.get("role_label") or ROLE_LABELS.get(role, role)
            if schedule_followup(payload, role_label):
                scheduled += 1
            else:
                skipped += 1
        except Exception as exc:
            print(f"[lead_followup] Inbox-Scan Fehler {path.name}: {exc}", flush=True)

    return {"scanned": scanned, "scheduled": scheduled, "skipped": skipped}


def run_maintenance() -> dict:
    """Vollständiger Wartungslauf: Inbox + fällige Sends + Resend-Nachplanung + Tagesfazit."""
    from lead_followup.schedule import process_due, retry_unscheduled
    from lead_followup.daily_digest import maybe_send_digest

    inbox = scan_inbox()
    retried = retry_unscheduled()
    sent = process_due()
    digest = maybe_send_digest()
    return {
        "inbox": inbox,
        "retried": retried,
        "sent": sent,
        "digest_sent": digest,
    }
