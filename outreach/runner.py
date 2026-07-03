#!/usr/bin/env python3
"""Kaplan Solutions — Outreach-Daemon (Baufirmen deutschlandweit anschreiben).

Nutzung:
  python -m outreach.runner once     # Ein Zyklus (finden → anreichern → senden)
  python -m outreach.runner daemon   # Endlosschleife im Hintergrund
  python -m outreach.runner status   # Statistik
  python -m outreach.runner report     # Tagesfazit sofort testen (--force)
  python -m outreach.runner midday     # Mittags-Update testen (--force)
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    if not os.getenv("RESEND_API_KEY") and not os.getenv("ADMIN_EMAIL"):
        try:
            load_dotenv(ROOT / ".env")
        except OSError as exc:
            print(f"[outreach] .env nicht lesbar ({exc}) — nutze System-Env", flush=True)
except ImportError:
    pass

from outreach import config
from outreach import discover
from outreach import enrich
from outreach import sender
from outreach import storage
from outreach import daily_report
from outreach import reliability
from outreach import reminder
from outreach import sheet_sync
from outreach import morning_report
from outreach import midday_report
from outreach import health


def _log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n"
    print(msg, flush=True)
    try:
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        with config.LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def run_cycle(last_run: float | None = None) -> float:
    now = time.time()
    try:
        storage.init_db()
    except sqlite3.OperationalError as exc:
        _log(f"[outreach] DB-Init-Wiederholung: {exc}")
        health.recover_db()
        storage.init_db()

    if last_run is not None:
        reliability.catch_up_after_gap(now - last_run)
    reliability.keep_awake_for_cycle()

    discovered = discover.discover_all_campaigns()
    enriched = enrich.enrich_batch(config.ENRICH_BATCH)
    sent = sender.send_batch()
    pending_sync = storage.count_unsynced_sent()
    sync_cap = config.SHEET_SYNC_BATCH
    if pending_sync > 30:
        sync_cap = min(pending_sync, config.SHEET_SYNC_BATCH * 6)
    elif pending_sync > 10:
        sync_cap = config.SHEET_SYNC_BATCH * 3
    synced = sheet_sync.sync_batch(limit=sync_cap)
    reminded = reminder.process_reminders()
    morning = morning_report.maybe_send_morning_report()
    midday = midday_report.maybe_send_midday_report()
    reported = daily_report.maybe_send_report()
    followups = 0
    try:
        from lead_followup.reconcile import run_maintenance

        result = run_maintenance()
        followups = result.get("sent", 0) + result.get("retried", 0)
        if result.get("digest_sent"):
            followups += 1
    except Exception as exc:
        _log(f"[lead_followup] Fehler: {exc}")
    try:
        from matching import maybe_run_match_cycle, maybe_send_briefing

        if maybe_run_match_cycle():
            followups += 1
        if maybe_send_briefing():
            followups += 1
    except Exception as exc:
        _log(f"[matching] Fehler: {exc}")
    if not any((discovered, enriched, sent, synced, reminded, reported, followups, morning, midday)):
        _log(
            "[outreach] Zyklus: nichts zu tun "
            f"({reliability.window_status_line()})"
        )
    health.record_success()
    return now


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
    if config.REFERRAL_ENABLED:
        print("--- Referral (Makler/Architekten/Ingenieure) ---")
        print(f"Gefunden heute:       {s['today_referral_discovered']} / {config.REFERRAL_DAILY_DISCOVER_LIMIT}")
        print(f"Versendet heute:      {s['today_referral_sent']} / {config.REFERRAL_DAILY_SEND_LIMIT}")
        print(f"In Warteschlange:     {s['referral_queued']}")
        print(f"Versendet (gesamt):   {s['referral_sent_all_time']}")
    if config.BAUHERR_ENABLED:
        print("--- Bauherr (Projektentwickler/Bauträger) ---")
        print(f"Gefunden heute:       {s.get('today_bauherr_discovered', 0)} / {config.BAUHERR_DAILY_DISCOVER_LIMIT}")
        print(f"Versendet heute:      {s.get('today_bauherr_sent', 0)} / {config.BAUHERR_DAILY_SEND_LIMIT}")
        print(f"In Warteschlange:     {s.get('bauherr_queued', 0)}")
        print(f"Versendet (gesamt):   {s.get('bauherr_sent_all_time', 0)}")
    ss = storage.sheet_sync_stats()
    print(f"Sheet-Portfolio:      {ss['synced']} sync, {ss['pending']} ausstehend")
    print(f"Zuverlässigkeit:      caffeinate={'an' if config.CAFFEINATE_ENABLED else 'aus'}, "
          f"wake-catchup={'an' if config.WAKE_CATCHUP_ENABLED else 'aus'}")
    print(f"Sendefenster:         {reliability.window_status_line()}")
    print(f"Reports:              Morgen 8 · Mittag 13 · Abend 18 Uhr")
    print(f"DB:                   {config.DB_PATH}")
    print(f"Log:                  {config.LOG_PATH}")


def cmd_daemon() -> None:
    _log(
        "[outreach] Daemon gestartet — "
        f"caffeinate={'an' if config.CAFFEINATE_ENABLED else 'aus'}, "
        f"wake-catchup={'an' if config.WAKE_CATCHUP_ENABLED else 'aus'}, "
        "reports=8/13/18"
    )
    last_run: float | None = None
    while True:
        try:
            last_run = run_cycle(last_run)
        except sqlite3.OperationalError as exc:
            _log(f"[outreach] SQLite-Fehler — Recovery: {exc}")
            health.record_error(exc)
            health.recover_db()
            time.sleep(3)
        except Exception as exc:
            _log(f"[outreach] Zyklus-Fehler: {exc}")
            if health.is_sqlite_io_error(exc):
                health.record_error(exc)
                health.recover_db()
            time.sleep(2)
        time.sleep(config.DAEMON_INTERVAL)


def main() -> None:
    parser = argparse.ArgumentParser(description="Kaplan Solutions B2B Outreach")
    parser.add_argument(
        "command",
        choices=("once", "daemon", "status", "unsubscribe", "report", "midday", "sync-sheet"),
        help="once=ein Zyklus, daemon=Hintergrund, status=Statistik, report=Tagesfazit, midday=Mittags-Update",
    )
    parser.add_argument("email", nargs="?", help="Nur für unsubscribe")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Report erneut senden (mit report oder midday)",
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
    elif args.command == "midday":
        storage.init_db()
        ok = midday_report.send_midday_report(force=args.force)
        sys.exit(0 if ok else 1)
    elif args.command == "sync-sheet":
        storage.init_db()
        total = 0
        while True:
            n = sheet_sync.sync_batch(limit=10)
            total += n
            pending = storage.sheet_sync_stats()["pending"]
            print(f"Batch: +{n}, gesamt neu: {total}, noch ausstehend: {pending}")
            if n == 0 or pending == 0:
                break
        sys.exit(0)
    elif args.command == "daemon":
        cmd_daemon()
    else:
        run_cycle()


if __name__ == "__main__":
    main()
