"""Gemeinsame SQLite-Einstellungen gegen Lock-/I/O-Fehler."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def connect(path: Path | str, *, row_factory: bool = False) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), timeout=60.0, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    if row_factory:
        conn.row_factory = sqlite3.Row
    return conn


def wal_checkpoint(path: Path | str) -> None:
    conn = sqlite3.connect(str(path), timeout=60.0)
    try:
        conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
        conn.commit()
    finally:
        conn.close()
