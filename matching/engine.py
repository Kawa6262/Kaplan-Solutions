"""Matching-Zyklus: Google Sheets via Webhook anstoßen."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from file_util import read_json, write_json_atomic
from matching import config

TZ = ZoneInfo("Europe/Berlin")
_STATE_PATH = Path(__file__).resolve().parent.parent / "data" / "matching_state.json"
_WEBHOOK_TIMEOUT = int(os.getenv("SHEETS_WEBHOOK_TIMEOUT", "120"))
_WEBHOOK_RETRIES = int(os.getenv("SHEETS_WEBHOOK_RETRIES", "3"))


def _load_state() -> dict:
    try:
        return read_json(_STATE_PATH)
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    write_json_atomic(_STATE_PATH, state)


def _post_action(action: str, extra: dict | None = None) -> dict:
    url = config.SHEETS_WEBHOOK_URL
    if not url or not url.rstrip("/").endswith("/exec"):
        return {"ok": False, "error": "SHEETS_WEBHOOK_URL fehlt oder ungültig"}

    payload = {"action": action}
    if extra:
        payload.update(extra)
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; KaplanSolutions/1.0)",
        },
        method="POST",
    )
    last_error = ""
    for attempt in range(1, _WEBHOOK_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=_WEBHOOK_TIMEOUT) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    import re
                    m = re.search(r"\{[\s\S]*\}", raw)
                    return json.loads(m.group(0)) if m else {"ok": False, "raw": raw[:300]}
        except urllib.error.HTTPError as exc:
            err = exc.read().decode("utf-8", errors="replace")
            return {"ok": False, "error": f"HTTP {exc.code}: {err[:300]}"}
        except Exception as exc:
            last_error = str(exc)
            if attempt < _WEBHOOK_RETRIES:
                time.sleep(2 * attempt)
    return {"ok": False, "error": last_error or "Webhook fehlgeschlagen"}


def trigger_match_rescan() -> dict:
    result = _post_action("match_rescan")
    if result.get("ok"):
        r = result.get("result") or {}
        print(
            f"[matching] Scan OK — {r.get('total_matches', 0)} Matches, "
            f"{r.get('hot', 0)} heiß",
            flush=True,
        )
    else:
        print(f"[matching] Scan fehlgeschlagen: {result.get('error', result)}", flush=True)
    return result


def trigger_daily_briefing() -> dict:
    result = _post_action("daily_briefing")
    if result.get("ok"):
        r = result.get("result") or {}
        print(
            f"[matching] Briefing gesendet — {r.get('hot', 0)} heiße Matches",
            flush=True,
        )
    else:
        print(f"[matching] Briefing fehlgeschlagen: {result.get('error', result)}", flush=True)
    return result


def maybe_run_match_cycle() -> bool:
    """Stündlicher Match-Rescan (Backup zum Apps-Script-Trigger)."""
    if not config.SHEETS_WEBHOOK_URL:
        return False
    state = _load_state()
    last = float(state.get("last_rescan", 0))
    now = time.time()
    if now - last < config.MATCH_RESCAN_INTERVAL:
        return False
    ok = trigger_match_rescan().get("ok", False)
    if ok:
        state["last_rescan"] = now
        _save_state(state)
    return ok


def maybe_send_briefing(force: bool = False) -> bool:
    """Tägliches Matching-Briefing um MATCH_BRIEFING_HOUR."""
    if not config.SHEETS_WEBHOOK_URL:
        return False
    now = datetime.now(TZ)
    if not force and now.hour < config.MATCH_BRIEFING_HOUR:
        return False

    day = now.date().isoformat()
    state = _load_state()
    if not force and state.get("briefing_day") == day:
        return False

    ok = trigger_daily_briefing().get("ok", False)
    if ok:
        state["briefing_day"] = day
        _save_state(state)
    return ok
