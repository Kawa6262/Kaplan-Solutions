"""Google-Sheet-Aktionen via Apps-Script-Webhook (CRM, Billing)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


def _webhook_url() -> str:
    return os.getenv("SHEETS_WEBHOOK_URL", "").strip()


def _crm_secret() -> str:
    return os.getenv("ADMIN_CRM_SECRET", "").strip()


def sheet_action(action: str, extra: dict | None = None) -> dict:
    url = _webhook_url()
    secret = _crm_secret()
    if not url or not secret:
        return {"ok": False, "error": "SHEETS_WEBHOOK_URL oder ADMIN_CRM_SECRET fehlt"}
    payload = {"action": action, "crm_secret": secret}
    if extra:
        payload.update(extra)
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; KaplanSolutions-Automation/1.0)",
    }
    timeout = int(os.getenv("SHEETS_WEBHOOK_TIMEOUT", "90"))
    try:
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw.strip() else {"ok": False, "error": "leere Antwort"}
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:400]
        except Exception:
            detail = str(exc)
        return {"ok": False, "error": f"HTTP {exc.code}: {detail}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def crm_update(ref: str, fields: dict) -> dict:
    return sheet_action("crm_update", {"ref": ref, "fields": fields})


def crm_snapshot() -> dict:
    return sheet_action("crm_snapshot")
