"""Idempotenz: welche Match-Alerts bereits gesendet wurden."""

from __future__ import annotations

from pathlib import Path

from file_util import read_json, write_json_atomic

_STORE = Path(__file__).resolve().parent.parent / "data" / "match_alerts_sent.json"
_MAX = 2000


def _load() -> set[str]:
    try:
        data = read_json(_STORE)
        return set(data if isinstance(data, list) else [])
    except Exception:
        return set()


def _save(ids: set[str]) -> None:
    trimmed = sorted(ids)[-_MAX:]
    write_json_atomic(_STORE, trimmed)


def already_sent(match_id: str) -> bool:
    return match_id in _load()


def mark_sent(match_id: str) -> None:
    ids = _load()
    ids.add(match_id)
    _save(ids)
