"""SQLite-Speicher für geplante Lead-Follow-ups."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator

from lead_followup.config import DATA_DIR, DB_PATH

_DB_READY = False


def init_db() -> None:
    global _DB_READY
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS lead_followups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ref TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL,
                name TEXT NOT NULL DEFAULT '',
                role TEXT NOT NULL DEFAULT '',
                company TEXT NOT NULL DEFAULT '',
                role_label TEXT NOT NULL DEFAULT '',
                received_at TEXT NOT NULL,
                scheduled_for TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                resend_id TEXT,
                sent_at TEXT,
                error TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_lead_followups_due
                ON lead_followups(status, scheduled_for);
            """
        )
        conn.commit()
    finally:
        conn.close()
    _DB_READY = True


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    if not _DB_READY:
        init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def insert_followup(
    *,
    ref: str,
    email: str,
    name: str,
    role: str,
    company: str,
    role_label: str,
    received_at: datetime,
    scheduled_for: datetime,
) -> bool:
    """Legt Follow-up an. Returns False wenn ref bereits existiert."""
    with _conn() as db:
        try:
            db.execute(
                """
                INSERT INTO lead_followups (
                    ref, email, name, role, company, role_label,
                    received_at, scheduled_for, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                """,
                (
                    ref,
                    email.strip().lower(),
                    name.strip(),
                    role.strip(),
                    company.strip(),
                    role_label.strip(),
                    received_at.isoformat(timespec="seconds"),
                    scheduled_for.isoformat(timespec="seconds"),
                ),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def get_by_ref(ref: str) -> sqlite3.Row | None:
    with _conn() as db:
        return db.execute(
            "SELECT * FROM lead_followups WHERE ref = ?", (ref,)
        ).fetchone()


def reset_to_pending(ref: str) -> None:
    with _conn() as db:
        db.execute(
            """
            UPDATE lead_followups
            SET status = 'pending', resend_id = NULL, error = NULL
            WHERE ref = ?
            """,
            (ref,),
        )


def pending_without_resend() -> list[sqlite3.Row]:
    with _conn() as db:
        return list(
            db.execute(
                """
                SELECT * FROM lead_followups
                WHERE status = 'pending' AND (resend_id IS NULL OR resend_id = '')
                ORDER BY scheduled_for ASC
                """
            ).fetchall()
        )


def mark_scheduled(ref: str, resend_id: str | None = None) -> None:
    with _conn() as db:
        db.execute(
            """
            UPDATE lead_followups
            SET status = 'scheduled', resend_id = ?
            WHERE ref = ?
            """,
            (resend_id, ref),
        )


def mark_sent(ref: str) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with _conn() as db:
        db.execute(
            """
            UPDATE lead_followups
            SET status = 'sent', sent_at = ?, error = NULL
            WHERE ref = ?
            """,
            (now, ref),
        )


def mark_failed(ref: str, error: str) -> None:
    with _conn() as db:
        db.execute(
            """
            UPDATE lead_followups
            SET status = 'failed', error = ?
            WHERE ref = ?
            """,
            (error[:500], ref),
        )


def due_pending() -> list[sqlite3.Row]:
    now = datetime.now().isoformat(timespec="seconds")
    with _conn() as db:
        return list(
            db.execute(
                """
                SELECT * FROM lead_followups
                WHERE status = 'pending' AND scheduled_for <= ?
                ORDER BY scheduled_for ASC
                """,
                (now,),
            ).fetchall()
        )


def stats() -> dict:
    with _conn() as db:
        rows = db.execute(
            """
            SELECT status, COUNT(*) AS cnt
            FROM lead_followups
            GROUP BY status
            """
        ).fetchall()
    out = {"pending": 0, "scheduled": 0, "sent": 0, "failed": 0, "total": 0}
    for row in rows:
        out[row["status"]] = int(row["cnt"])
        out["total"] += int(row["cnt"])
    return out
