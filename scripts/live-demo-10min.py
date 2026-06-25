#!/usr/bin/env python3
"""10-Minuten-Livedemo: finden, anreichern, senden, dann Tagesfazit."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")
# Demo: Versandfenster für Testlauf öffnen
os.environ["OUTREACH_HOUR_START"] = "0"
os.environ["OUTREACH_HOUR_END"] = "24"
os.environ["OUTREACH_WEEKDAYS_ONLY"] = "0"

from outreach import config  # noqa: E402
from outreach import daily_report  # noqa: E402
from outreach import discover  # noqa: E402
from outreach import enrich  # noqa: E402
from outreach import sender  # noqa: E402
from outreach import storage  # noqa: E402

DURATION = int(os.getenv("LIVE_DEMO_SECONDS", "600"))
INTERVAL = int(os.getenv("LIVE_DEMO_INTERVAL", "25"))


def _log(msg: str) -> None:
    print(f"{time.strftime('%H:%M:%S')} {msg}", flush=True)


def main() -> None:
    storage.init_db()
    _log(f"=== Live-Demo gestartet ({DURATION // 60} Min.) ===")
    _log(f"Warteschlange: {storage.stats_summary()['queued']} | Limit heute: {config.DAILY_SEND_LIMIT}")

    start = time.time()
    sent_total = 0

    while time.time() - start < DURATION:
        storage.init_db()
        discover.discover_batch()
        enrich.enrich_batch(config.ENRICH_BATCH)
        if sender.send_one():
            sent_total += 1
        remaining = int(DURATION - (time.time() - start))
        s = storage.stats_summary()
        _log(
            f"Stand: {s['today_sent']} gesendet heute | "
            f"{s['queued']} in Warteschlange | noch {remaining}s"
        )
        if s["today_sent"] >= config.DAILY_SEND_LIMIT:
            _log("Tageslimit erreicht — warte bis Demo-Ende.")
            time.sleep(min(INTERVAL, max(1, remaining)))
            continue
        if remaining <= 0:
            break
        time.sleep(min(INTERVAL, remaining))

    _log("=== Demo beendet — Tagesfazit wird gesendet ===")
    ok = daily_report.send_daily_report(force=True)
    s = storage.stats_summary()
    _log(f"Fazit: {'gesendet' if ok else 'FEHLER'} | Heute versendet: {s['today_sent']}")
    _log(f"Insgesamt in dieser Demo: {sent_total} Mails")


if __name__ == "__main__":
    main()
