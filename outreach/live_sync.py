"""Mac → Cloud: Outreach-Dashboard für Kaplan Sales auf Render aktualisieren."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from outreach import config, dashboard

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


def _compact_payload(payload: dict) -> dict:
    out = dict(payload)
    max_sends = int(os.getenv("OUTREACH_LIVE_SYNC_SENDS", "800"))
    sends = list(out.get("sends") or [])
    if len(sends) > max_sends:
        out["sends"] = sends[:max_sends]
        out["sends_truncated"] = True
    return out


def _push_render(payload: dict) -> dict:
    base = os.getenv("COMPANY_WEBSITE", "https://kaplan-solutions.de").strip().rstrip("/")
    crm = os.getenv("ADMIN_CRM_SECRET", "").strip()
    cron = os.getenv("CRON_SECRET", "").strip()
    if not crm and not cron:
        return {"ok": False, "error": "Kein Secret für Render-Push"}

    url = f"{base}/api/outreach/push"
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "KaplanSolutions-OutreachLiveSync/1.0",
    }
    if crm:
        headers["X-Admin-Crm-Secret"] = crm
    if cron:
        headers["X-Cron-Secret"] = cron
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw.strip() else {"ok": True, "via": "render"}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        return {"ok": False, "error": f"HTTP {exc.code}: {detail}", "via": "render"}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "via": "render"}


def _push_sheet(payload: dict) -> dict:
    from sheet_client import sheet_action

    result = sheet_action("outreach_live_save", {"payload": payload})
    if result.get("ok") and result.get("bytes") is not None:
        result["via"] = "sheet"
        return result
    if result.get("junk"):
        return {
            "ok": False,
            "error": "Apps Script: outreach_live_save deployen (google-leads-automation.gs)",
            "via": "sheet",
        }
    if result.get("ok"):
        return result
    result["via"] = "sheet"
    return result


def push_to_cloud(*, force: bool = False) -> dict:
    """Snapshot an Render und/oder Google Sheet (Fallback)."""
    if not _sync_enabled():
        return {"ok": False, "skipped": True, "reason": "OUTREACH_LIVE_SYNC aus"}

    if not force and time.time() - _last_push_ts() < _MIN_INTERVAL_SEC:
        return {"ok": True, "skipped": True, "reason": "throttled"}

    payload = _compact_payload(
        dashboard.gather_dashboard(
            campaign="all",
            day="all",
            sends_limit=int(os.getenv("OUTREACH_LIVE_SYNC_SENDS", "800")),
            source="mac_sync",
        )
    )

    render = _push_render(payload)
    if render.get("ok"):
        _mark_pushed()
        return render

    sheet = _push_sheet(payload)
    if sheet.get("ok"):
        _mark_pushed()
        return sheet

    return {
        "ok": False,
        "error": sheet.get("error") or render.get("error") or "Sync fehlgeschlagen",
        "render": render.get("error"),
        "sheet": sheet.get("error"),
    }


def push_if_due(*, force: bool = False) -> dict:
    return push_to_cloud(force=force)
