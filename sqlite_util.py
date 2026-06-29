"""Gemeinsame SQLite-Einstellungen gegen Lock-/I/O-Fehler."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def connect(path: Path | str, *, row_factory: bool = False) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA synchronous=NORMAL")
    if row_factory:
        conn.row_factory = sqlite3.Row
    return conn
