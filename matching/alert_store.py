"""Idempotenz: welche Match-Alerts bereits gesendet wurden."""

from __future__ import annotations

import json
from pathlib import Path

_STORE = Path(__file__).resolve().parent.parent / "data" / "match_alerts_sent.json"
_MAX = 2000


def _load() -> set[str]:
    try:
        data = json.loads(_STORE.read_text(encoding="utf-8"))
        return set(data if isinstance(data, list) else [])
    except Exception:
        return set()


def _save(ids: set[str]) -> None:
    _STORE.parent.mkdir(parents=True, exist_ok=True)
    trimmed = sorted(ids)[-_MAX:]
    _STORE.write_text(json.dumps(trimmed, indent=0), encoding="utf-8")


def already_sent(match_id: str) -> bool:
    return match_id in _load()


def mark_sent(match_id: str) -> None:
    ids = _load()
    ids.add(match_id)
    _save(ids)
