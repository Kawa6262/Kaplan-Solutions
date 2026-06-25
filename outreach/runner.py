#!/usr/bin/env python3
"""Kaplan Solutions — Outreach-Daemon (Baufirmen deutschlandweit anschreiben).

Nutzung:
  python -m outreach.runner once     # Ein Zyklus (finden → anreichern → senden)
  python -m outreach.runner daemon   # Endlosschleife im Hintergrund
  python -m outreach.runner status   # Statistik
  python -m outreach.runner report     # Tagesfazit sofort testen (--force)
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from outreach import config
from outreach import discover
from outreach import enrich
from outreach import sender
from outreach import storage
from outreach import daily_report


def _log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n"
    print(msg, flush=True)
    try:
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        with config.LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def run_cycle() -> None:
    storage.init_db()
    discovered = discover.discover_batch()
    enriched = enrich.enrich_batch(config.ENRICH_BATCH)
    sent = sender.send_one()
    reported = daily_report.maybe_send_report()
    followups = 0
    try:
        from lead_followup.reconcile import run_maintenance

        result = run_maintenance()
        followups = result.get("sent", 0) + result.get("retried", 0)
    except Exception as exc:
        _log(f"[lead_followup] Fehler: {exc}")
    if not any((discovered, enriched, sent, reported, followups)):
        _log("[outreach] Zyklus: nichts zu tun (Limit erreicht oder außerhalb Geschäftszeiten).")


def cmd_status() -> None:
    storage.init_db()
    s = storage.stats_summary()
    print("=== Kaplan Solutions Outreach ===")
    print(f"Gesamt Prospects:     {s['total']}")
    print(f"Versendet (gesamt):   {s['sent_all_time']}")
    print(f"In Warteschlange:     {s['queued']}")
    print(f"Neu / ohne E-Mail:    {s['new']}")
    print(f"Übersprungen:         {s['skipped']}")
    print(f"Fehlgeschlagen:       {s['failed']}")
    print("--- Heute ---")
    print(f"Gefunden:             {s['today_discovered']} / {config.DAILY_DISCOVER_LIMIT}")
    print(f"Angereichert:         {s['today_enriched']}")
    print(f"Versendet:            {s['today_sent']} / {config.DAILY_SEND_LIMIT}")
    print(f"DB:                   {config.DB_PATH}")
    print(f"Log:                  {config.LOG_PATH}")


def cmd_daemon() -> None:
    _log("[outreach] Daemon gestartet — Ctrl+C zum Beenden.")
    while True:
        try:
            run_cycle()
        except Exception as exc:
            _log(f"[outreach] Zyklus-Fehler: {exc}")
        time.sleep(config.DAEMON_INTERVAL)


def main() -> None:
    parser = argparse.ArgumentParser(description="Kaplan Solutions B2B Outreach")
    parser.add_argument(
        "command",
        choices=("once", "daemon", "status", "unsubscribe", "report"),
        help="once=ein Zyklus, daemon=Hintergrund, status=Statistik, report=Tagesfazit",
    )
    parser.add_argument("email", nargs="?", help="Nur für unsubscribe")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Tagesfazit erneut senden (nur mit report)",
    )
    args = parser.parse_args()

    if args.command == "status":
        cmd_status()
    elif args.command == "unsubscribe":
        if not args.email:
            print("E-Mail angeben: python -m outreach.runner unsubscribe firma@example.de")
            sys.exit(1)
        storage.init_db()
        storage.add_unsubscribe(args.email)
        print(f"Abgemeldet: {args.email}")
    elif args.command == "report":
        storage.init_db()
        ok = daily_report.send_daily_report(force=args.force)
        sys.exit(0 if ok else 1)
    elif args.command == "daemon":
        cmd_daemon()
    else:
        run_cycle()


if __name__ == "__main__":
    main()
