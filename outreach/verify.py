"""Abgleich: DB-Versand vs. Resend-Zustellung (Beweis, dass Mails wirklich rausgehen)."""

from __future__ import annotations

import json
import os
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

from outreach import config

TZ = ZoneInfo("Europe/Berlin")


def _resend_recent(limit: int = 50) -> list[dict]:
    key = os.getenv("RESEND_API_KEY", "").strip()
    if not key:
        return []
    req = urllib.request.Request(
        f"https://api.resend.com/emails?limit={limit}",
        headers={
            "Authorization": f"Bearer {key}",
            "User-Agent": "KaplanSolutions/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
            return data.get("data") or []
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return []


def verify_delivery(sample: int = 20) -> dict:
    """Vergleicht letzte DB-Sends mit Resend-API (delivered/bounced)."""
    storage_path = config.DB_PATH
    conn = sqlite3.connect(storage_path)
    conn.row_factory = sqlite3.Row
    today = datetime.now(TZ).strftime("%Y-%m-%d")

    db_today = conn.execute(
        """
        SELECT COUNT(*) AS n FROM prospects
        WHERE status = 'sent' AND date(sent_at) = ?
        """,
        (today,),
    ).fetchone()["n"]

    db_total = conn.execute(
        "SELECT COUNT(*) AS n FROM prospects WHERE status = 'sent'"
    ).fetchone()["n"]

    recent_db = conn.execute(
        """
        SELECT sent_at, email, company_name, campaign FROM prospects
        WHERE status = 'sent' ORDER BY sent_at DESC LIMIT ?
        """,
        (sample,),
    ).fetchall()

    resend = _resend_recent(min(100, sample * 3))
    by_to: dict[str, dict] = {}
    for item in resend:
        to_list = item.get("to") or []
        if to_list:
            by_to[to_list[0].lower()] = item

    matched = 0
    delivered = 0
    lines: list[str] = []
    for row in recent_db[:sample]:
        email = (row["email"] or "").lower()
        hit = by_to.get(email)
        if hit:
            matched += 1
            event = hit.get("last_event") or "?"
            if event == "delivered":
                delivered += 1
            lines.append(
                f"  ✓ {row['company_name'][:40]} → {email} | Resend: {event}"
            )
        else:
            lines.append(
                f"  ? {row['company_name'][:40]} → {email} | (noch nicht in Resend-Liste)"
            )

    resend_delivered = sum(1 for e in resend if e.get("last_event") == "delivered")
    resend_bounced = sum(
        1 for e in resend if e.get("last_event") in ("bounced", "failed", "complained")
    )

    return {
        "today_db": int(db_today),
        "total_db": int(db_total),
        "resend_sample": len(resend),
        "resend_delivered": resend_delivered,
        "resend_bounced": resend_bounced,
        "matched": matched,
        "delivered_matched": delivered,
        "lines": lines,
    }


def print_report(sample: int = 15) -> None:
    r = verify_delivery(sample)
    print("=== Versand-Verifikation (DB ↔ Resend API) ===")
    print(f"Heute in DB als 'sent':     {r['today_db']}")
    print(f"Gesamt versendet (DB):      {r['total_db']}")
    print(
        f"Resend (letzte {r['resend_sample']}): "
        f"{r['resend_delivered']} delivered, {r['resend_bounced']} bounced/failed"
    )
    print(f"Abgleich letzte {sample} DB-Einträge: {r['delivered_matched']}/{r['matched']} in Resend bestätigt")
    print()
    for line in r["lines"]:
        print(line)
    print()
    if r["resend_delivered"] > 0 and r["today_db"] > 0:
        print("→ Mails gehen REAL über Resend raus (API-Status 'delivered').")
    elif not os.getenv("RESEND_API_KEY"):
        print("→ RESEND_API_KEY fehlt — Verifikation nur über DB möglich.")
