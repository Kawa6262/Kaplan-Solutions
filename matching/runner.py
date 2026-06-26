#!/usr/bin/env python3
"""Matching-CLI — Rescan & Briefing testen."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from matching.engine import maybe_run_match_cycle, maybe_send_briefing, trigger_daily_briefing, trigger_match_rescan


def main() -> None:
    parser = argparse.ArgumentParser(description="Kaplan Matching")
    parser.add_argument("command", choices=("rescan", "briefing", "cycle"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.command == "rescan":
        ok = trigger_match_rescan().get("ok", False)
    elif args.command == "briefing":
        ok = trigger_daily_briefing().get("ok", False) if args.force else maybe_send_briefing(force=True)
    else:
        ok = maybe_run_match_cycle() or maybe_send_briefing(force=args.force)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
