"""Konfiguration für automatische Lead-Follow-up-Mails."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "lead_followups.db"

FOLLOWUP_HOUR = int(os.getenv("LEAD_FOLLOWUP_HOUR", "8"))
FOLLOWUP_MINUTE = int(os.getenv("LEAD_FOLLOWUP_MINUTE", "0"))
AGENT_NAME = os.getenv(
    "LEAD_AGENT_NAME",
    "Kaplan Solutions · Partnervermittlung",
).strip()
REPLY_EMAIL = os.getenv("REPLY_EMAIL", "kontakt@kaplan-solutions.de").strip()
