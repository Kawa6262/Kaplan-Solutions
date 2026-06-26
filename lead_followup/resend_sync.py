"""Resend-Status mit lokaler DB abgleichen."""

from __future__ import annotations

import json
import os
import urllib.request

from lead_followup import storage

DELIVERED_EVENTS = frozenset({"delivered", "sent", "opened", "clicked"})
FAILED_EVENTS = frozenset({"bounced", "failed", "complained", "canceled"})


def _fetch_status(resend_id: str) -> str | None:
    key = os.getenv("RESEND_API_KEY", "").strip()
    if not key or not resend_id:
        return None
    req = urllib.request.Request(
        f"https://api.resend.com/emails/{resend_id}",
        headers={
            "Authorization": f"Bearer {key}",
            "User-Agent": "Mozilla/5.0 (compatible; KaplanSolutions/1.0)",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode())
            return (data.get("last_event") or "").lower()
    except Exception:
        return None


def sync_scheduled_status() -> int:
    """Aktualisiert DB aus Resend. Returns Anzahl geänderter Einträge."""
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    TZ = ZoneInfo("Europe/Berlin")
    storage.init_db()
    updated = 0
    now = datetime.now(TZ)

    for row in storage.scheduled_with_resend():
        event = _fetch_status(row["resend_id"])
        if event in DELIVERED_EVENTS:
            storage.mark_sent(row["ref"])
            updated += 1
            continue
        if event in FAILED_EVENTS:
            storage.mark_failed(row["ref"], f"Resend: {event}")
            updated += 1
            continue

        # Nach Versandfenster + Puffer: Resend meldet oft verzögert — als gesendet werten
        try:
            scheduled = datetime.fromisoformat(row["scheduled_for"])
            if scheduled.tzinfo is None:
                scheduled = scheduled.replace(tzinfo=TZ)
            else:
                scheduled = scheduled.astimezone(TZ)
            if now >= scheduled + timedelta(minutes=20):
                storage.mark_sent(row["ref"])
                updated += 1
        except Exception:
            pass

    return updated
