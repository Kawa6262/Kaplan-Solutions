"""Billing CLI."""

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

from billing.runner import generate_and_send_invoice, process_due_invoices
from sheet_client import crm_snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description="Kaplan Solutions Rechnungsgenerator")
    parser.add_argument("command", choices=("scan", "send"))
    parser.add_argument("--ref", help="Anfrage-Nr. für einzelne Rechnung")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.command == "scan":
        result = process_due_invoices(force=args.force)
        print(result)
        sys.exit(0 if result.get("ok") else 1)

    if not args.ref:
        print("Bitte --ref KS-2026-XXXX angeben")
        sys.exit(1)
    snap = crm_snapshot()
    lead = next((l for l in (snap.get("leads") or []) if l.get("ref") == args.ref), None)
    if not lead:
        print(f"Lead {args.ref} nicht gefunden")
        sys.exit(1)
    result = generate_and_send_invoice(lead, force=args.force)
    print(result)
    sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
