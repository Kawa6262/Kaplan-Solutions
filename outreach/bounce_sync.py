"""Bounces & Beschwerden aus Resend → Abmeldeliste (schützt Domain-Reputation)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from outreach import storage

FAILED_EVENTS = frozenset({"bounced", "failed", "complained"})


def _resend_recent(limit: int = 100) -> list[dict]:
    key = os.getenv("RESEND_API_KEY", "").strip()
    if not key:
        return []
    req = urllib.request.Request(
        f"https://api.resend.com/emails?limit={limit}",
        headers={
            "Authorization": f"Bearer {key}",
            "User-Agent": "KaplanSolutions/1.0",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
            return data.get("data") or []
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return []


def sync_bounces(limit: int = 100) -> int:
    """Trägt Bounces/Beschwerden in die Abmeldeliste ein. Returns Anzahl neu."""
    storage.init_db()
    added = 0
    for item in _resend_recent(limit):
        event = (item.get("last_event") or "").lower()
        if event not in FAILED_EVENTS:
            continue
        to_list = item.get("to") or []
        if not to_list:
            continue
        email = to_list[0].strip().lower()
        if not email or storage.is_unsubscribed(email):
            continue
        storage.add_unsubscribe(email)
        added += 1
        print(f"[outreach] ⛔ {event} → Abmeldeliste: {email}", flush=True)
    return added
