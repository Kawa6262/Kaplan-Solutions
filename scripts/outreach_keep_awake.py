#!/usr/bin/env python3
"""Zusätzlicher Sleep-Schutz werktags 9–18 Uhr (LaunchAgent)."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from outreach import config  # noqa: E402


def main() -> None:
    now = datetime.now(ZoneInfo("Europe/Berlin"))
    if config.SEND_WEEKDAYS_ONLY and now.weekday() >= 5:
        return
    if not (config.SEND_HOUR_START <= now.hour < config.SEND_HOUR_END):
        return

    end = now.replace(hour=config.SEND_HOUR_END, minute=5, second=0, microsecond=0)
    seconds = max(60, int((end - now).total_seconds()))
    subprocess.run(
        ["caffeinate", "-dimsu", "-t", str(seconds)],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


if __name__ == "__main__":
    main()
