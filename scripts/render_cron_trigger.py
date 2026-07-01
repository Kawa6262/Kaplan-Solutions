#!/usr/bin/env python3
"""Render Cron → HTTP-Trigger für Web-Service-Jobs (Outreach, Billing)."""

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

JOBS = {
    "outreach": "/api/cron/outreach",
    "billing": "/api/cron/billing",
    "followups": "/api/cron/lead-followups",
}


def main() -> None:
    job = (sys.argv[1] if len(sys.argv) > 1 else "outreach").strip().lower()
    path = JOBS.get(job)
    if not path:
        print(f"Unbekannter Job: {job}. Erlaubt: {', '.join(JOBS)}")
        sys.exit(1)

    base = os.getenv("COMPANY_WEBSITE", "https://kaplan-solutions.de").strip().rstrip("/")
    secret = os.getenv("CRON_SECRET", "").strip()
    if not secret:
        print("CRON_SECRET fehlt")
        sys.exit(1)

    url = f"{base}{path}"
    req = urllib.request.Request(
        url,
        data=b"{}",
        headers={
            "Content-Type": "application/json",
            "X-Cron-Secret": secret,
            "User-Agent": "KaplanSolutions-RenderCron/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            print(body)
            data = json.loads(body) if body.strip() else {}
            sys.exit(0 if data.get("ok", True) else 1)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        print(f"HTTP {exc.code}: {detail}")
        sys.exit(1)


if __name__ == "__main__":
    main()
