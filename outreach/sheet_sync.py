"""Outreach-Partner automatisch ins Google Sheet (Matching-Portfolio)."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

from outreach import config
from outreach import storage
from outreach.branche import categorize

TZ = ZoneInfo("Europe/Berlin")
_WEBHOOK = os.getenv("SHEETS_WEBHOOK_URL", "").strip()
_TIMEOUT = int(os.getenv("SHEETS_WEBHOOK_TIMEOUT", "90"))
_RETRIES = int(os.getenv("SHEETS_WEBHOOK_RETRIES", "2"))
_BATCH = int(os.getenv("OUTREACH_SHEET_SYNC_BATCH", "5"))


def _enabled() -> bool:
    return (
        os.getenv("OUTREACH_SHEET_SYNC", "1").strip().lower() not in ("0", "false", "no")
        and bool(_WEBHOOK)
        and _WEBHOOK.rstrip("/").endswith("/exec")
    )


def _payload_from_row(row) -> dict:
    trade = (row["trade"] or "").strip()
    city = (row["city"] or "").strip()
    company = (row["company_name"] or "").strip()
    branche = categorize(trade or company)
    now = datetime.now(TZ).strftime("%d.%m.%Y %H:%M")
    return {
        "action": "import_outreach",
        "eingegangen": now,
        "email": (row["email"] or "").strip().lower(),
        "firma": company,
        "contact_name": company,
        "telefon": (row["phone"] or "").strip() or "—",
        "stadt": city or "-",
        "plz": "",
        "branche": branche,
        "gewerke": trade or branche,
        "nachricht": (
            f"Automatisch aus Outreach-Portfolio importiert "
            f"(Gewerk: {trade or 'Bau'}, Quelle: Google Places)."
        ),
        "outreach_id": int(row["id"]),
    }


def _post(payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        _WEBHOOK,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; KaplanSolutions/1.0)",
        },
        method="POST",
    )
    last = ""
    for attempt in range(1, _RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return {"ok": False, "raw": raw[:300]}
        except urllib.error.HTTPError as exc:
            err = exc.read().decode("utf-8", errors="replace")
            return {"ok": False, "error": f"HTTP {exc.code}: {err[:200]}"}
        except Exception as exc:
            last = str(exc)
            if attempt < _RETRIES:
                time.sleep(2 * attempt)
    return {"ok": False, "error": last or "Webhook fehlgeschlagen"}


def sync_prospect(row) -> bool:
    """Einzelnen Partner ins Sheet. Returns True wenn neu importiert."""
    if not _enabled():
        return False
    if storage.is_sheet_synced(int(row["id"])):
        return False

    result = _post(_payload_from_row(row))
    if not result.get("ok"):
        print(
            f"[outreach] Sheet-Sync fehlgeschlagen {row['company_name']}: "
            f"{result.get('error', result)}",
            flush=True,
        )
        return False

    if result.get("skipped"):
        storage.mark_sheet_synced(int(row["id"]), result.get("ref", "duplicate"))
        return False

    ref = result.get("ref", "")
    matches = int(result.get("matches") or 0)
    storage.mark_sheet_synced(int(row["id"]), ref)
    print(
        f"[outreach] Sheet ✓ {row['company_name']} → {ref} "
        f"({matches} potenzielle Matches)",
        flush=True,
    )
    return True


def sync_batch(limit: int | None = None) -> int:
    """Importiert ausstehende versendete Prospects ins Sheet."""
    if not _enabled():
        return 0
    cap = limit if limit is not None else _BATCH
    count = 0
    for row in storage.unsynced_sent(limit=cap):
        if sync_prospect(row):
            count += 1
        time.sleep(0.8)
    return count
