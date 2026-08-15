"""Mac → Cloud: Outreach-Dashboard für Kaplan Sales auf Render aktualisieren."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from outreach import config, dashboard

ROOT = config.ROOT
LAST_PUSH_PATH = config.DATA_DIR / "outreach_live_last_push.txt"
_MIN_INTERVAL_SEC = int(os.getenv("OUTREACH_LIVE_SYNC_INTERVAL", "60"))


def _sync_enabled() -> bool:
    return os.getenv("OUTREACH_LIVE_SYNC", "1").strip().lower() not in ("0", "false", "no")


def _last_push_ts() -> float:
    try:
        return float(LAST_PUSH_PATH.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return 0.0


def _mark_pushed() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    LAST_PUSH_PATH.write_text(str(time.time()), encoding="utf-8")


def push_to_cloud(*, force: bool = False) -> dict:
    """POST Dashboard-Snapshot an Render (CRON_SECRET)."""
    if not _sync_enabled():
        return {"ok": False, "skipped": True, "reason": "OUTREACH_LIVE_SYNC aus"}

    if not force and time.time() - _last_push_ts() < _MIN_INTERVAL_SEC:
        return {"ok": True, "skipped": True, "reason": "throttled"}

    base = os.getenv("COMPANY_WEBSITE", "https://kaplan-solutions.de").strip().rstrip("/")
    secret = os.getenv("CRON_SECRET", "").strip()
    if not secret:
        return {"ok": False, "error": "CRON_SECRET fehlt für Live-Sync"}

    payload = dashboard.gather_dashboard(
        campaign="all",
        day="all",
        sends_limit=int(os.getenv("OUTREACH_LIVE_SYNC_SENDS", "2500")),
        source="mac_sync",
    )

    url = f"{base}/api/outreach/push"
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Cron-Secret": secret,
            "User-Agent": "KaplanSolutions-OutreachLiveSync/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            result = json.loads(raw) if raw.strip() else {"ok": True}
            if result.get("ok"):
                _mark_pushed()
            return result
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        return {"ok": False, "error": f"HTTP {exc.code}: {detail}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def push_if_due(*, force: bool = False) -> dict:
    return push_to_cloud(force=force)
