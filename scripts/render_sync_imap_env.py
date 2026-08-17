#!/usr/bin/env python3
"""IMAP/Reply-E-Mail-Variablen aus .env nach Render pushen (API-Key nötig)."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

API = "https://api.render.com/v1"
SERVICE_NAME = os.getenv("RENDER_SERVICE_NAME", "kaplan-solutions").strip()
SERVICE_ID = os.getenv("RENDER_SERVICE_ID", "").strip()

KEYS = (
    "REPLY_EMAIL",
    "CONTACT_EMAIL",
    "IMAP_HOST",
    "IMAP_PORT",
    "IMAP_USER",
    "IMAP_PASSWORD",
    "IMAP_FOLDER",
    "IMAP_LOOKBACK_DAYS",
)


def _req(method: str, path: str, body: dict | list | None = None) -> object:
    key = os.getenv("RENDER_API_KEY", "").strip()
    if not key:
        print("RENDER_API_KEY fehlt — Account Settings → API Keys auf render.com")
        sys.exit(1)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{API}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "KaplanSolutions/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def _service_id() -> str:
    if SERVICE_ID:
        return SERVICE_ID
    page = 1
    while True:
        payload = _req("GET", f"/services?limit=100&page={page}")
        for svc in payload if isinstance(payload, list) else payload.get("items", []):
            if svc.get("name") == SERVICE_NAME or svc.get("slug") == SERVICE_NAME:
                return svc["id"]
        if not isinstance(payload, list) and not payload.get("hasMore"):
            break
        page += 1
    print(f"Service '{SERVICE_NAME}' nicht gefunden — RENDER_SERVICE_ID setzen")
    sys.exit(1)


def main() -> None:
    updates = {k: os.getenv(k, "").strip() for k in KEYS if os.getenv(k, "").strip()}
    if not updates.get("IMAP_PASSWORD"):
        print("IMAP_PASSWORD in .env fehlt")
        sys.exit(1)

    sid = _service_id()
    try:
        existing = _req("GET", f"/services/{sid}/env-vars")
    except urllib.error.HTTPError as exc:
        print(f"Env lesen fehlgeschlagen: {exc}")
        sys.exit(1)

    merged: dict[str, str] = {}
    for item in existing if isinstance(existing, list) else existing.get("envVars", existing):
        merged[item["key"]] = item.get("value") or ""
    merged.update(updates)
    body = [{"key": k, "value": v} for k, v in sorted(merged.items())]

    try:
        _req("PUT", f"/services/{sid}/env-vars", body)
    except urllib.error.HTTPError as exc:
        err = exc.read().decode(errors="replace")
        print(f"Env schreiben fehlgeschlagen ({exc.code}): {err[:400]}")
        sys.exit(1)

    print(f"Render OK — {len(updates)} Variablen gesetzt für {SERVICE_NAME} ({sid}):")
    for k in sorted(updates):
        if k == "IMAP_PASSWORD":
            print(f"  {k}=***")
        else:
            print(f"  {k}={updates[k]}")
    print("Im Render-Dashboard: Save and deploy auslösen (falls nicht automatisch).")


if __name__ == "__main__":
    main()
