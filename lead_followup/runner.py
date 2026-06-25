"""Lead-Follow-up — CLI."""

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

from lead_followup import storage
from lead_followup.schedule import process_due, schedule_followup
from lead_followup.reconcile import run_maintenance


def cmd_status() -> None:
    storage.init_db()
    s = storage.stats()
    print("=== Lead Follow-up ===")
    print(f"Gesamt:     {s['total']}")
    print(f"Geplant:    {s['scheduled']} (Resend)")
    print(f"Wartend:    {s['pending']} (Daemon)")
    print(f"Gesendet:   {s['sent']}")
    print(f"Fehler:     {s['failed']}")


def cmd_process() -> None:
    result = run_maintenance()
    print(result)


def cmd_maintain() -> None:
    result = run_maintenance()
    print(f"Lead-Follow-up Wartung: {result}")


def cmd_test() -> None:
    ok = schedule_followup(
        {
            "ref": "TEST-FOLLOWUP",
            "name": "Max Mustermann",
            "email": __import__("os").getenv("ADMIN_EMAIL", ""),
            "role": "bauherr",
            "project": "Sanierung",
            "location": "Berlin",
        },
        "Auftraggeber (Bauherr)",
    )
    sys.exit(0 if ok else 1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Kaplan Solutions Lead Follow-up")
    parser.add_argument("command", choices=("status", "process", "maintain", "test"))
    args = parser.parse_args()
    if args.command == "status":
        cmd_status()
    elif args.command == "process":
        cmd_process()
    elif args.command == "maintain":
        cmd_maintain()
    else:
        cmd_test()


if __name__ == "__main__":
    main()
