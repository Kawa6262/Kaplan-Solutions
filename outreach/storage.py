"""SQLite-Speicher für Prospects, Versandstatus und Abmeldungen."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from typing import Iterator

from outreach import config
from outreach.config import DB_PATH, DATA_DIR
from sqlite_util import connect as sqlite_connect

_DB_READY = False


def init_db() -> None:
    global _DB_READY
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite_connect(DB_PATH)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS prospects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                place_id TEXT UNIQUE,
                company_name TEXT NOT NULL,
                city TEXT,
                trade TEXT,
                website TEXT,
                email TEXT,
                phone TEXT,
                status TEXT NOT NULL DEFAULT 'new',
                created_at TEXT NOT NULL,
                enriched_at TEXT,
                sent_at TEXT,
                failed_at TEXT,
                error TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_prospects_status ON prospects(status);
            CREATE INDEX IF NOT EXISTS idx_prospects_email ON prospects(email);

            CREATE TABLE IF NOT EXISTS unsubscribes (
                email TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS search_cursor (
                id INTEGER PRIMARY KEY,
                trade_idx INTEGER NOT NULL DEFAULT 0,
                city_idx INTEGER NOT NULL DEFAULT 0,
                next_page_token TEXT
            );

            CREATE TABLE IF NOT EXISTS daily_counters (
                day TEXT PRIMARY KEY,
                discovered INTEGER NOT NULL DEFAULT 0,
                enriched INTEGER NOT NULL DEFAULT 0,
                sent INTEGER NOT NULL DEFAULT 0,
                report_sent INTEGER NOT NULL DEFAULT 0,
                referral_discovered INTEGER NOT NULL DEFAULT 0,
                referral_enriched INTEGER NOT NULL DEFAULT 0,
                referral_sent INTEGER NOT NULL DEFAULT 0
            );

            INSERT OR IGNORE INTO search_cursor (id, trade_idx, city_idx) VALUES (1, 0, 0);
            INSERT OR IGNORE INTO search_cursor (id, trade_idx, city_idx) VALUES (2, 0, 0);
            """
        )
        conn.commit()
        _migrate_columns(conn)
        _DB_READY = True
    finally:
        conn.close()


def _migrate_columns(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(daily_counters)")}
    if "report_sent" not in cols:
        conn.execute(
            "ALTER TABLE daily_counters ADD COLUMN report_sent INTEGER NOT NULL DEFAULT 0"
        )
    prospect_cols = {row[1] for row in conn.execute("PRAGMA table_info(prospects)")}
    if "failed_at" not in prospect_cols:
        conn.execute("ALTER TABLE prospects ADD COLUMN failed_at TEXT")
    if "sheet_ref" not in prospect_cols:
        conn.execute("ALTER TABLE prospects ADD COLUMN sheet_ref TEXT")
    if "sheet_synced_at" not in prospect_cols:
        conn.execute("ALTER TABLE prospects ADD COLUMN sheet_synced_at TEXT")
    if "reminder_sent_at" not in prospect_cols:
        conn.execute("ALTER TABLE prospects ADD COLUMN reminder_sent_at TEXT")
    if "campaign" not in prospect_cols:
        conn.execute(
            "ALTER TABLE prospects ADD COLUMN campaign TEXT NOT NULL DEFAULT 'partner'"
        )
    counter_cols = {row[1] for row in conn.execute("PRAGMA table_info(daily_counters)")}
    for col in ("referral_discovered", "referral_enriched", "referral_sent"):
        if col not in counter_cols:
            conn.execute(
                f"ALTER TABLE daily_counters ADD COLUMN {col} INTEGER NOT NULL DEFAULT 0"
            )
    for col in ("bauherr_discovered", "bauherr_enriched", "bauherr_sent", "morning_report_sent"):
        if col not in counter_cols:
            conn.execute(
                f"ALTER TABLE daily_counters ADD COLUMN {col} INTEGER NOT NULL DEFAULT 0"
            )
    conn.execute("INSERT OR IGNORE INTO search_cursor (id, trade_idx, city_idx) VALUES (2, 0, 0)")
    conn.execute("INSERT OR IGNORE INTO search_cursor (id, trade_idx, city_idx) VALUES (3, 0, 0)")
    conn.commit()


_COUNTER_MAP = {
    "partner": {
        "discovered": "discovered",
        "enriched": "enriched",
        "sent": "sent",
    },
    "referral": {
        "discovered": "referral_discovered",
        "enriched": "referral_enriched",
        "sent": "referral_sent",
    },
    "bauherr": {
        "discovered": "bauherr_discovered",
        "enriched": "bauherr_enriched",
        "sent": "bauherr_sent",
    },
}

_CURSOR_IDS = {
    "partner": 1,
    "referral": 2,
    "bauherr": 3,
}


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    if not _DB_READY:
        init_db()
    conn = sqlite_connect(DB_PATH, row_factory=True)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _today() -> str:
    return date.today().isoformat()


def _counter_column(field: str, campaign: str = "partner") -> str:
    return _COUNTER_MAP.get(campaign, _COUNTER_MAP["partner"]).get(field, field)


def get_counter(field: str, campaign: str = "partner") -> int:
    col = _counter_column(field, campaign)
    today = _today()
    with _conn() as db:
        row = db.execute(
            f"SELECT {col} AS v FROM daily_counters WHERE day = ?",
            (today,),
        ).fetchone()
        if not row:
            return 0
        return int(row["v"] or 0)


def bump_counter(field: str, n: int = 1, campaign: str = "partner") -> None:
    col = _counter_column(field, campaign)
    today = _today()
    with _conn() as db:
        db.execute(
            """
            INSERT INTO daily_counters (day, discovered, enriched, sent)
            VALUES (?, 0, 0, 0)
            ON CONFLICT(day) DO NOTHING
            """,
            (today,),
        )
        db.execute(
            f"UPDATE daily_counters SET {col} = {col} + ? WHERE day = ?",
            (n, today),
        )


def is_unsubscribed(email: str) -> bool:
    with _conn() as db:
        row = db.execute(
            "SELECT 1 FROM unsubscribes WHERE lower(email) = lower(?)",
            (email.strip(),),
        ).fetchone()
        return row is not None


def add_unsubscribe(email: str) -> None:
    email = email.strip().lower()
    if not email:
        return
    with _conn() as db:
        db.execute(
            "INSERT OR IGNORE INTO unsubscribes (email, created_at) VALUES (?, ?)",
            (email, datetime.now().isoformat(timespec="seconds")),
        )
        db.execute(
            "UPDATE prospects SET status = 'unsubscribed' WHERE lower(email) = ?",
            (email,),
        )


def upsert_prospect(
    *,
    place_id: str,
    company_name: str,
    city: str,
    trade: str,
    website: str = "",
    phone: str = "",
    campaign: str = "partner",
) -> bool:
    """Returns True if newly inserted."""
    now = datetime.now().isoformat(timespec="seconds")
    stored_id = place_id
    if campaign == config.CAMPAIGN_REFERRAL:
        stored_id = f"referral:{place_id}"
    elif campaign == config.CAMPAIGN_BAUHERR:
        stored_id = f"bauherr:{place_id}"
    with _conn() as db:
        cur = db.execute(
            """
            INSERT OR IGNORE INTO prospects
                (place_id, company_name, city, trade, website, phone, status, created_at, campaign)
            VALUES (?, ?, ?, ?, ?, ?, 'new', ?, ?)
            """,
            (stored_id, company_name, city, trade, website, phone, now, campaign),
        )
        return cur.rowcount > 0


def get_search_cursor(campaign: str = "partner") -> tuple[int, int, str | None]:
    cursor_id = _CURSOR_IDS.get(campaign, 1)
    with _conn() as db:
        row = db.execute(
            "SELECT trade_idx, city_idx, next_page_token FROM search_cursor WHERE id = ?",
            (cursor_id,),
        ).fetchone()
        if not row:
            return 0, 0, None
        return int(row["trade_idx"]), int(row["city_idx"]), row["next_page_token"]


def set_search_cursor(
    trade_idx: int,
    city_idx: int,
    next_page_token: str | None,
    campaign: str = "partner",
) -> None:
    cursor_id = _CURSOR_IDS.get(campaign, 1)
    with _conn() as db:
        db.execute(
            """
            UPDATE search_cursor
            SET trade_idx = ?, city_idx = ?, next_page_token = ?
            WHERE id = ?
            """,
            (trade_idx, city_idx, next_page_token, cursor_id),
        )


def prospects_to_enrich(limit: int) -> list[sqlite3.Row]:
    with _conn() as db:
        return list(
            db.execute(
                """
                SELECT * FROM prospects
                WHERE status = 'new' AND website IS NOT NULL AND website != ''
                ORDER BY CASE campaign WHEN 'partner' THEN 0 ELSE 1 END, id ASC
                LIMIT ?
                """,
                (limit,),
            )
        )


def mark_no_website(place_id: str) -> None:
    with _conn() as db:
        db.execute(
            "UPDATE prospects SET status = 'skipped' WHERE place_id = ?",
            (place_id,),
        )


def mark_enriched(prospect_id: int, email: str | None, status: str) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with _conn() as db:
        db.execute(
            """
            UPDATE prospects
            SET email = ?, status = ?, enriched_at = ?
            WHERE id = ?
            """,
            (email, status, now, prospect_id),
        )


def next_to_send(campaign: str = "partner") -> sqlite3.Row | None:
    cities = config.GERMAN_CITIES
    placeholders = ",".join("?" * len(cities))
    with _conn() as db:
        return db.execute(
            f"""
            SELECT * FROM prospects
            WHERE status = 'queued'
              AND campaign = ?
              AND email IS NOT NULL AND email != ''
              AND city IN ({placeholders})
            ORDER BY enriched_at ASC
            LIMIT 1
            """,
            [campaign, *cities],
        ).fetchone()


def mark_sent(prospect_id: int) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with _conn() as db:
        db.execute(
            "UPDATE prospects SET status = 'sent', sent_at = ? WHERE id = ?",
            (now, prospect_id),
        )


def is_sheet_synced(prospect_id: int) -> bool:
    with _conn() as db:
        row = db.execute(
            "SELECT sheet_synced_at FROM prospects WHERE id = ?", (prospect_id,)
        ).fetchone()
    return bool(row and row["sheet_synced_at"])


def mark_sheet_synced(prospect_id: int, ref: str = "") -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with _conn() as db:
        db.execute(
            """
            UPDATE prospects
            SET sheet_ref = ?, sheet_synced_at = ?
            WHERE id = ?
            """,
            (ref[:64], now, prospect_id),
        )


def unsynced_sent(limit: int = 20) -> list[sqlite3.Row]:
    with _conn() as db:
        return list(
            db.execute(
                """
                SELECT * FROM prospects
                WHERE status = 'sent'
                  AND campaign = 'partner'
                  AND email IS NOT NULL AND email != ''
                  AND sheet_synced_at IS NULL
                ORDER BY sent_at ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        )


def mark_reminder_sent(prospect_id: int) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with _conn() as db:
        db.execute(
            "UPDATE prospects SET reminder_sent_at = ? WHERE id = ?",
            (now, prospect_id),
        )


def due_for_reminder(days: int = 3, limit: int = 5) -> list[sqlite3.Row]:
    from datetime import timedelta

    cutoff = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")
    with _conn() as db:
        return list(
            db.execute(
                """
                SELECT * FROM prospects
                WHERE status = 'sent'
                  AND campaign = 'partner'
                  AND email IS NOT NULL AND email != ''
                  AND reminder_sent_at IS NULL
                  AND sent_at IS NOT NULL
                  AND sent_at <= ?
                ORDER BY sent_at ASC
                LIMIT ?
                """,
                (cutoff, limit),
            ).fetchall()
        )


def sheet_sync_stats() -> dict:
    with _conn() as db:
        row = db.execute(
            """
            SELECT
                SUM(CASE WHEN status = 'sent' AND sheet_synced_at IS NOT NULL THEN 1 ELSE 0 END) AS synced,
                SUM(CASE WHEN status = 'sent' AND sheet_synced_at IS NULL THEN 1 ELSE 0 END) AS pending
            FROM prospects
            """
        ).fetchone()
    return {
        "synced": int(row["synced"] or 0),
        "pending": int(row["pending"] or 0),
    }


def mark_failed(prospect_id: int, error: str) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with _conn() as db:
        db.execute(
            "UPDATE prospects SET status = 'failed', error = ?, failed_at = ? WHERE id = ?",
            (error[:500], now, prospect_id),
        )


def stats_summary() -> dict:
    with _conn() as db:
        totals = db.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) AS sent,
                SUM(CASE WHEN status = 'queued' THEN 1 ELSE 0 END) AS queued,
                SUM(CASE WHEN status = 'new' THEN 1 ELSE 0 END) AS new_count,
                SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END) AS skipped,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed,
                SUM(CASE WHEN campaign = 'referral' AND status = 'sent' THEN 1 ELSE 0 END) AS referral_sent_all,
                SUM(CASE WHEN campaign = 'referral' AND status = 'queued' THEN 1 ELSE 0 END) AS referral_queued,
                SUM(CASE WHEN campaign = 'bauherr' AND status = 'sent' THEN 1 ELSE 0 END) AS bauherr_sent_all,
                SUM(CASE WHEN campaign = 'bauherr' AND status = 'queued' THEN 1 ELSE 0 END) AS bauherr_queued,
                SUM(CASE WHEN campaign = 'partner' AND status = 'queued' THEN 1 ELSE 0 END) AS partner_queued
            FROM prospects
            """
        ).fetchone()
        today = db.execute(
            """
            SELECT discovered, enriched, sent,
                   referral_discovered, referral_enriched, referral_sent,
                   bauherr_discovered, bauherr_enriched, bauherr_sent
            FROM daily_counters WHERE day = ?
            """,
            (_today(),),
        ).fetchone()
    return {
        "total": int(totals["total"] or 0),
        "sent_all_time": int(totals["sent"] or 0),
        "queued": int(totals["queued"] or 0),
        "new": int(totals["new_count"] or 0),
        "skipped": int(totals["skipped"] or 0),
        "failed": int(totals["failed"] or 0),
        "referral_sent_all_time": int(totals["referral_sent_all"] or 0),
        "referral_queued": int(totals["referral_queued"] or 0),
        "bauherr_sent_all_time": int(totals["bauherr_sent_all"] or 0),
        "bauherr_queued": int(totals["bauherr_queued"] or 0),
        "partner_queued": int(totals["partner_queued"] or 0),
        "today_discovered": int(today["discovered"] if today else 0),
        "today_enriched": int(today["enriched"] if today else 0),
        "today_sent": int(today["sent"] if today else 0),
        "today_referral_discovered": int(today["referral_discovered"] if today else 0),
        "today_referral_enriched": int(today["referral_enriched"] if today else 0),
        "today_referral_sent": int(today["referral_sent"] if today else 0),
        "today_bauherr_discovered": int((today["bauherr_discovered"] if today else 0) or 0),
        "today_bauherr_sent": int((today["bauherr_sent"] if today else 0) or 0),
    }


def get_daily_counters(day: str) -> dict:
    with _conn() as db:
        row = db.execute(
            """
            SELECT discovered, enriched, sent, report_sent,
                   referral_discovered, referral_enriched, referral_sent,
                   bauherr_discovered, bauherr_enriched, bauherr_sent,
                   morning_report_sent
            FROM daily_counters WHERE day = ?
            """,
            (day,),
        ).fetchone()
    if not row:
        return {
            "discovered": 0,
            "enriched": 0,
            "sent": 0,
            "report_sent": 0,
            "referral_discovered": 0,
            "referral_enriched": 0,
            "referral_sent": 0,
            "bauherr_discovered": 0,
            "bauherr_enriched": 0,
            "bauherr_sent": 0,
            "morning_report_sent": 0,
        }
    return {
        "discovered": int(row["discovered"]),
        "enriched": int(row["enriched"]),
        "sent": int(row["sent"]),
        "report_sent": int(row["report_sent"]),
        "referral_discovered": int(row["referral_discovered"] or 0),
        "referral_enriched": int(row["referral_enriched"] or 0),
        "referral_sent": int(row["referral_sent"] or 0),
        "bauherr_discovered": int(row["bauherr_discovered"] or 0),
        "bauherr_enriched": int(row["bauherr_enriched"] or 0),
        "bauherr_sent": int(row["bauherr_sent"] or 0),
        "morning_report_sent": int(row["morning_report_sent"] or 0),
    }


def report_was_sent(day: str) -> bool:
    return get_daily_counters(day).get("report_sent", 0) > 0


def mark_report_sent(day: str) -> None:
    with _conn() as db:
        db.execute(
            """
            INSERT INTO daily_counters (day, discovered, enriched, sent, report_sent)
            VALUES (?, 0, 0, 0, 1)
            ON CONFLICT(day) DO UPDATE SET report_sent = 1
            """,
            (day,),
        )


def mark_morning_report_sent(day: str) -> None:
    with _conn() as db:
        db.execute(
            """
            INSERT INTO daily_counters (day, discovered, enriched, sent, morning_report_sent)
            VALUES (?, 0, 0, 0, 1)
            ON CONFLICT(day) DO UPDATE SET morning_report_sent = 1
            """,
            (day,),
        )


def _row_val(row: sqlite3.Row, key: str, default: str = "") -> str:
    try:
        val = row[key]
        return val if val is not None else default
    except (KeyError, IndexError):
        return default


def _rows_to_companies(rows: list) -> list[dict]:
    out = []
    for row in rows:
        ts = (
            _row_val(row, "sent_at")
            or _row_val(row, "failed_at")
            or _row_val(row, "enriched_at")
        )
        time_part = ts.split("T")[1][:5] if "T" in ts else ""
        out.append({
            "name": _row_val(row, "company_name"),
            "city": _row_val(row, "city"),
            "trade": _row_val(row, "trade"),
            "email": _row_val(row, "email"),
            "time": time_part,
            "error": _row_val(row, "error"),
        })
    return out


def prospects_sent_on_day(day: str) -> list[dict]:
    with _conn() as db:
        rows = list(
            db.execute(
                """
                SELECT company_name, city, trade, email, sent_at, failed_at, enriched_at, error
                FROM prospects
                WHERE status = 'sent' AND sent_at LIKE ?
                ORDER BY sent_at ASC
                """,
                (f"{day}%",),
            )
        )
    return _rows_to_companies(rows)


def prospects_failed_on_day(day: str) -> list[dict]:
    with _conn() as db:
        rows = list(
            db.execute(
                """
                SELECT company_name, city, trade, email, sent_at, failed_at, enriched_at, error
                FROM prospects
                WHERE status = 'failed' AND failed_at LIKE ?
                ORDER BY failed_at ASC
                """,
                (f"{day}%",),
            )
        )
    return _rows_to_companies(rows)


def skipped_on_day(day: str) -> int:
    with _conn() as db:
        row = db.execute(
            """
            SELECT COUNT(*) AS c FROM prospects
            WHERE status = 'skipped' AND created_at LIKE ?
            """,
            (f"{day}%",),
        ).fetchone()
    return int(row["c"] or 0)


def sent_breakdown_by_city(day: str) -> list[dict]:
    with _conn() as db:
        rows = db.execute(
            """
            SELECT city, COUNT(*) AS count
            FROM prospects
            WHERE status = 'sent' AND sent_at LIKE ? AND city IS NOT NULL AND city != ''
            GROUP BY city
            ORDER BY count DESC
            LIMIT 10
            """,
            (f"{day}%",),
        ).fetchall()
    return [{"city": r["city"], "count": int(r["count"])} for r in rows]


def sent_breakdown_by_trade(day: str) -> list[dict]:
    with _conn() as db:
        rows = db.execute(
            """
            SELECT trade, COUNT(*) AS count
            FROM prospects
            WHERE status = 'sent' AND sent_at LIKE ? AND trade IS NOT NULL AND trade != ''
            GROUP BY trade
            ORDER BY count DESC
            LIMIT 10
            """,
            (f"{day}%",),
        ).fetchall()
    return [{"trade": r["trade"], "count": int(r["count"])} for r in rows]


def unsubscribe_count() -> int:
    with _conn() as db:
        row = db.execute("SELECT COUNT(*) AS c FROM unsubscribes").fetchone()
    return int(row["c"] or 0)
