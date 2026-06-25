"""Baufirmen über Google Places API (New) finden."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from places_api import text_search

from outreach import config
from outreach import storage


def discover_batch() -> int:
    """Sucht neue Firmen. Returns Anzahl neu gespeicherter Prospects."""
    if not config.GOOGLE_PLACES_KEY:
        print("[outreach] GOOGLE_PLACES_API_KEY fehlt — Discovery übersprungen.", flush=True)
        return 0

    if storage.get_counter("discovered") >= config.DAILY_DISCOVER_LIMIT:
        return 0

    trade_idx, city_idx, page_token = storage.get_search_cursor()
    trade = config.TRADE_QUERIES[trade_idx % len(config.TRADE_QUERIES)]
    city = config.GERMAN_CITIES[city_idx % len(config.GERMAN_CITIES)]
    query = f"{trade} {city}"

    results, next_token, error = text_search(query, page_token)
    if error:
        print(f"[outreach] Places-Fehler für {query}: {error}", flush=True)
        _advance_cursor(trade_idx, city_idx, None)
        return 0
    if not results and not page_token:
        _advance_cursor(trade_idx, city_idx, None)
        return 0

    inserted = 0
    for item in results:
        if storage.get_counter("discovered") >= config.DAILY_DISCOVER_LIMIT:
            break
        place_id = item["place_id"]
        name = item["name"]
        website = item["website"]
        phone = item["phone"]
        if storage.upsert_prospect(
            place_id=place_id,
            company_name=name,
            city=city,
            trade=trade,
            website=website,
            phone=phone,
        ):
            inserted += 1
            storage.bump_counter("discovered")
            if not website:
                storage.mark_no_website(place_id)

    if next_token:
        storage.set_search_cursor(trade_idx, city_idx, next_token)
    else:
        _advance_cursor(trade_idx, city_idx, None)

    if inserted:
        print(f"[outreach] +{inserted} Firmen ({query})", flush=True)
    return inserted


def _advance_cursor(trade_idx: int, city_idx: int, token: str | None) -> None:
    if token:
        storage.set_search_cursor(trade_idx, city_idx, token)
        return
    city_idx += 1
    if city_idx >= len(config.GERMAN_CITIES):
        city_idx = 0
        trade_idx += 1
    storage.set_search_cursor(trade_idx, city_idx, None)
