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

    # Immer und mit Vorrang laden: launchd übergibt eine zum Installationszeitpunkt
    # eingefrorene Kopie der Variablen. Ohne override liefen Änderungen an der
    # .env ins Leere, weil der Daemon still die alten Werte weiterbenutzt hätte.
    try:
        load_dotenv(ROOT / ".env", override=True)
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
from outreach import bounce_sync
from outreach import sheet_sync
from outreach import morning_report
from outreach import midday_report
from outreach import health
from outreach import power
from outreach import quality
from outreach import replies
from outreach import system_state


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
        gap = now - last_run
        power.report_gap(gap)
        reliability.catch_up_after_gap(gap)
    reliability.keep_awake_for_cycle()
    power.check_power(reliability.in_send_window_now())

    discovered = discover.discover_all_campaigns()
    enriched = enrich.enrich_batch(config.ENRICH_BATCH)
    reminded = reminder.process_reminders()
    bounced = bounce_sync.sync_bounces()
    answered = replies.check_replies()
    try:
        from business_model import contract_inbox
        contracts = contract_inbox.check_contract_returns()
    except Exception as exc:
        contracts = 0
        _log(f"[outreach] Vertrags-Postfach: {exc}")
    try:
        from business_model.contract_send import finalize_due_scheduled_contracts
        scheduled_contracts = finalize_due_scheduled_contracts()
        if scheduled_contracts:
            _log(f"[outreach] Geplante Verträge abgeschlossen: {scheduled_contracts}")
    except Exception as exc:
        _log(f"[outreach] Geplante Verträge: {exc}")
    if config.PROJEKT_ENABLED:
        quality.backfill_ratings(config.CAMPAIGN_PROJEKT, limit=config.PROJEKT_RATING_BATCH)
    sent = sender.send_batch()
    pending_sync = storage.count_unsynced_sent()
    sync_cap = config.SHEET_SYNC_BATCH
    if pending_sync > 30:
        sync_cap = min(pending_sync, config.SHEET_SYNC_BATCH * 6)
    elif pending_sync > 10:
        sync_cap = config.SHEET_SYNC_BATCH * 3
    synced = sheet_sync.sync_batch(limit=sync_cap)
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
    try:
        from outreach import live_sync

        sync_result = live_sync.push_if_due(force=bool(sent))
        if sync_result.get("ok") and not sync_result.get("skipped"):
            _log("[outreach] CRM Live-Sync ✓")
    except Exception as exc:
        _log(f"[outreach] CRM Live-Sync: {exc}")
    health.record_success()
    system_state.record_cycle_ok()
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
    if config.PROJEKT_ENABLED:
        from outreach.projekt import AKTUELL

        print(f"--- Projekt-Ausschreibung ({AKTUELL.referenz}, {AKTUELL.region}) ---")
        print(f"Gefunden heute:       {s.get('today_projekt_discovered', 0)} / {config.PROJEKT_DAILY_DISCOVER_LIMIT}")
        print(f"Versendet heute:      {s.get('today_projekt_sent', 0)} / {config.PROJEKT_DAILY_SEND_LIMIT}")
        print(f"In Warteschlange:     {s.get('projekt_queued', 0)}")
        print(f"Ohne E-Mail (neu):    {s.get('projekt_new', 0)}")
        print(f"Versendet (gesamt):   {s.get('projekt_sent_all_time', 0)}")
        print(f"Suchgebiet:           {len(config.PROJEKT_CITIES)} Städte, {len(config.PROJEKT_TRADE_QUERIES)} Gewerke")
    ss = storage.sheet_sync_stats()
    print(f"Sheet-Portfolio:      {ss['synced']} sync, {ss['pending']} ausstehend")
    print(f"Zuverlässigkeit:      caffeinate={'an' if config.CAFFEINATE_ENABLED else 'aus'}, "
          f"wake-catchup={'an' if config.WAKE_CATCHUP_ENABLED else 'aus'}")
    print(f"Sendefenster:         {reliability.window_status_line()}")
    print(f"Reports:              Health 8:30 · Watchdog 10/13/15/17 · Morgen 8 · Mittag 13 · Abend 18")
    print(f"DB:                   {config.DB_PATH}")
    print(f"Log:                  {config.LOG_PATH}")


def cmd_test_projekt() -> int:
    """Echte Projektmail an die Admin-Adresse — kein Prospect wird als versendet markiert."""
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    from mailer import email_configured, send_email
    from outreach.projekt_templates import build_bodies, build_subject

    storage.init_db()
    admin = os.getenv("ADMIN_EMAIL", "").strip()
    if not email_configured() or not admin:
        print("ADMIN_EMAIL oder Mailversand nicht konfiguriert.")
        return 1

    # Vorschau immer als Generalunternehmer in Duisburg — so sieht die Prioritäts-Mail aus.
    company, city, trade = "Musterbau GmbH", "Duisburg", "Generalunternehmer Bau"

    subject = build_subject(company, city)
    text, html = build_bodies(company, city, trade, recipient_email=admin, prospect_id=0)
    send_email(admin, f"[TEST] {subject}", text, html)
    print(f"Testmail → {admin}")
    print(f"Inhalt wie an: {company} · {city} · {trade}")
    print(f"Betreff im Original: {subject}")
    return 0


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
        choices=("once", "daemon", "status", "verify", "unsubscribe", "report", "midday", "sync-sheet", "healthcheck", "watchdog", "preview-projekt", "test-projekt", "replies"),
        help="once, daemon, status, healthcheck (8:30), watchdog (Versand-Überwachung)",
    )
    parser.add_argument("email", nargs="?", help="Nur für unsubscribe")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Report erneut senden (mit report, midday oder healthcheck)",
    )
    args = parser.parse_args()

    if args.command == "status":
        cmd_status()
    elif args.command == "verify":
        try:
            from dotenv import load_dotenv

            load_dotenv(ROOT / ".env")
        except Exception:
            pass
        from outreach import verify as verify_delivery

        verify_delivery.print_report()
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
    elif args.command == "healthcheck":
        storage.init_db()
        from outreach import daily_health_check

        ok = daily_health_check.run_daily_health_check(force=args.force)
        sys.exit(0 if ok else 1)
    elif args.command == "watchdog":
        storage.init_db()
        from outreach import watchdog

        ok = watchdog.run_watchdog(force=args.force)
        sys.exit(0 if ok else 1)
    elif args.command == "replies":
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
        storage.init_db()
        if not replies.configured():
            print("IMAP-Zugang fehlt — IMAP_HOST/IMAP_USER/IMAP_PASSWORD in .env setzen.")
            sys.exit(1)
        n = replies.check_replies()
        print(f"{n} neue Firmenantworten verarbeitet")
    elif args.command == "test-projekt":
        sys.exit(cmd_test_projekt())
    elif args.command == "preview-projekt":
        from outreach import projekt_preview

        projekt_preview.write_preview()
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
