"""Konfiguration Matching & Briefing."""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

SHEETS_WEBHOOK_URL = os.getenv("SHEETS_WEBHOOK_URL", "").strip()
MATCH_RESCAN_INTERVAL = int(os.getenv("MATCH_RESCAN_INTERVAL", "3600"))  # Sekunden
MATCH_BRIEFING_HOUR = int(os.getenv("MATCH_BRIEFING_HOUR", "10"))
MATCH_BRIEFING_EMAIL = os.getenv(
    "MATCH_BRIEFING_EMAIL",
    os.getenv("OUTREACH_REPORT_EMAIL", os.getenv("ADMIN_EMAIL", "")),
).strip()
MATCH_ALERT_MIN_SCORE = int(os.getenv("MATCH_ALERT_MIN_SCORE", "75"))
MATCH_ALERT_SECRET = os.getenv("MATCH_ALERT_SECRET", os.getenv("CRON_SECRET", "")).strip()
SITE_URL = os.getenv("COMPANY_WEBSITE", "https://kaplan-solutions.de").strip().rstrip("/")
