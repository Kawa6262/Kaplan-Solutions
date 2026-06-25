#!/usr/bin/env python3
"""Versand bis Mitternacht (Berlin), dann Tagesfazit, dann normaler Daemon."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")
os.environ["OUTREACH_HOUR_START"] = "0"
os.environ["OUTREACH_HOUR_END"] = "24"
os.environ["OUTREACH_WEEKDAYS_ONLY"] = "0"

from outreach import config  # noqa: E402
from outreach import daily_report  # noqa: E402
from outreach import discover  # noqa: E402
from outreach import enrich  # noqa: E402
from outreach import sender  # noqa: E402
from outreach import storage  # noqa: E402

TZ = ZoneInfo("Europe/Berlin")
SEND_INTERVAL = int(os.getenv("OVERNIGHT_SEND_INTERVAL", "12"))
LOG_PATH = ROOT / "data" / "overnight.log"


def _log(msg: str) -> None:
    line = f"{datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _midnight_tonight() -> datetime:
    now = datetime.now(TZ)
    return datetime.combine(now.date() + timedelta(days=1), datetime.min.time(), tzinfo=TZ)


def _seconds_until_midnight() -> float:
    return max(0.0, (_midnight_tonight() - datetime.now(TZ)).total_seconds())


def main() -> None:
    storage.init_db()
    report_day = datetime.now(TZ).date()
    midnight = _midnight_tonight()
    s = storage.stats_summary()

    _log("=== Nacht-Versand bis Mitternacht gestartet ===")
    _log(f"Warteschlange: {s['queued']} | Heute schon gesendet: {s['today_sent']}/{config.DAILY_SEND_LIMIT}")
    _log(f"Mitternacht: {midnight.strftime('%d.%m.%Y %H:%M')} | Fazit für: {report_day.isoformat()}")

    sent_session = 0
    while datetime.now(TZ) < midnight:
        s = storage.stats_summary()

        if s["today_sent"] < config.DAILY_SEND_LIMIT and s["queued"] > 0:
            if sender.send_one():
                sent_session += 1
                # Direkt nächste Mail — kein Warten wenn noch was in der Queue ist
                continue

        remaining = int(_seconds_until_midnight())
        s = storage.stats_summary()
        _log(
            f"Stand: {s['today_sent']}/{config.DAILY_SEND_LIMIT} heute | "
            f"{s['queued']} Warteschlange | +{sent_session} diese Session | "
            f"noch {remaining // 60}m {remaining % 60}s"
        )

        if s["today_sent"] >= config.DAILY_SEND_LIMIT:
            _log("Tageslimit erreicht — warte bis Mitternacht für Fazit.")
            time.sleep(min(30, max(1, remaining)))
            continue

        if s["queued"] == 0:
            discover.discover_batch()
            enrich.enrich_batch(min(5, config.ENRICH_BATCH))

        if remaining <= 0:
            break
        time.sleep(min(SEND_INTERVAL, remaining))

    # Kurz nach Mitternacht warten, damit der Tag sauber wechselt
    while datetime.now(TZ) < midnight:
        time.sleep(1)

    _log("=== Mitternacht — Tagesfazit wird gesendet ===")
    ok = daily_report.send_daily_report(for_day=report_day, force=True)
    s = storage.stats_summary()
    _log(f"Fazit: {'gesendet' if ok else 'FEHLER'} | {report_day}: {s['today_sent'] if report_day == datetime.now(TZ).date() else 'siehe DB'} versendet")

    # Normaler Daemon (9–18 Uhr werktags) für morgen
    setup = ROOT / "scripts" / "setup-outreach-daemon.sh"
    if setup.is_file():
        _log("=== Starte normalen Hintergrund-Daemon (9–18 Uhr) ===")
        result = subprocess.run(["bash", str(setup)], cwd=ROOT, capture_output=True, text=True)
        _log(result.stdout.strip() or result.stderr.strip() or "Daemon gestartet.")

    _log(f"=== Fertig. Diese Session: {sent_session} Mails gesendet ===")


if __name__ == "__main__":
    main()
