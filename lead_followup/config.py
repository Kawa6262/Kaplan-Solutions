"""Konfiguration für automatische Lead-Follow-up-Mails."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "lead_followups.db"

FOLLOWUP_HOUR = int(os.getenv("LEAD_FOLLOWUP_HOUR", "8"))
FOLLOWUP_MINUTE = int(os.getenv("LEAD_FOLLOWUP_MINUTE", "0"))
# Tagesfazit: erst wenn alle 8-Uhr-Follow-ups fertig sind (Fallback siehe unten)
DIGEST_HOUR = int(os.getenv("LEAD_DIGEST_HOUR", "9"))
DIGEST_MINUTE = int(os.getenv("LEAD_DIGEST_MINUTE", "0"))
DIGEST_FALLBACK_HOUR = int(os.getenv("LEAD_DIGEST_FALLBACK_HOUR", "10"))
DIGEST_GRACE_MINUTES = int(os.getenv("LEAD_DIGEST_GRACE_MINUTES", "15"))
AGENT_NAME = os.getenv(
    "LEAD_AGENT_NAME",
    "Kaplan Solutions · Partnervermittlung",
).strip()
REPLY_EMAIL = os.getenv("REPLY_EMAIL", "kontakt@kaplan-solutions.de").strip()
DIGEST_EMAIL = os.getenv(
    "LEAD_DIGEST_EMAIL",
    os.getenv("OUTREACH_REPORT_EMAIL", os.getenv("ADMIN_EMAIL", "")),
).strip()
