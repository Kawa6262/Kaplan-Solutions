"""Baufirmen und Referral-Partner über Google Places API (New) finden."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from places_api import text_search

from outreach import config
from outreach import storage


def _campaign_config(campaign: str) -> tuple[list[str], int, int]:
    if campaign == config.CAMPAIGN_REFERRAL:
        return (
            config.REFERRAL_TRADE_QUERIES,
            config.REFERRAL_DAILY_DISCOVER_LIMIT,
            config.REFERRAL_DISCOVER_BATCHES_PER_CYCLE,
        )
    if campaign == config.CAMPAIGN_BAUHERR:
        return (
            config.BAUHERR_TRADE_QUERIES,
            config.BAUHERR_DAILY_DISCOVER_LIMIT,
            config.BAUHERR_DISCOVER_BATCHES_PER_CYCLE,
        )
    return (
        config.TRADE_QUERIES,
        config.DAILY_DISCOVER_LIMIT,
        config.DISCOVER_BATCHES_PER_CYCLE,
    )


def discover_batch(campaign: str = config.CAMPAIGN_PARTNER) -> int:
    """Sucht neue Firmen. Returns Anzahl neu gespeicherter Prospects."""
    if campaign == config.CAMPAIGN_REFERRAL and not config.REFERRAL_ENABLED:
        return 0
    if campaign == config.CAMPAIGN_BAUHERR and not config.BAUHERR_ENABLED:
        return 0
    if not config.GOOGLE_PLACES_KEY:
        print("[outreach] GOOGLE_PLACES_API_KEY fehlt — Discovery übersprungen.", flush=True)
        return 0

    trades, discover_limit, _ = _campaign_config(campaign)
    if not trades:
        return 0

    if storage.get_counter("discovered", campaign) >= discover_limit:
        return 0

    trade_idx, city_idx, page_token = storage.get_search_cursor(campaign)
    trade = trades[trade_idx % len(trades)]
    city = config.GERMAN_CITIES[city_idx % len(config.GERMAN_CITIES)]
    query = f"{trade} {city}"

    results, next_token, error = text_search(query, page_token)
    if error:
        print(f"[outreach] Places-Fehler für {query} ({campaign}): {error}", flush=True)
        _advance_cursor(trade_idx, city_idx, None, len(trades), campaign)
        return 0
    if not results and not page_token:
        _advance_cursor(trade_idx, city_idx, None, len(trades), campaign)
        return 0

    inserted = 0
    for item in results:
        if storage.get_counter("discovered", campaign) >= discover_limit:
            break
        place_id = item["place_id"]
        name = item["name"]
        website = item["website"]
        phone = item["phone"]
        if not website and not phone:
            continue
        if storage.upsert_prospect(
            place_id=place_id,
            company_name=name,
            city=city,
            trade=trade,
            website=website,
            phone=phone,
            campaign=campaign,
        ):
            inserted += 1
            storage.bump_counter("discovered", campaign=campaign)
            if not website:
                prefix = campaign
                storage.mark_no_website(f"{prefix}:{place_id}" if prefix != config.CAMPAIGN_PARTNER else place_id)

    if next_token:
        storage.set_search_cursor(trade_idx, city_idx, next_token, campaign)
    else:
        _advance_cursor(trade_idx, city_idx, None, len(trades), campaign)

    label = {"referral": "Referral", "bauherr": "Bauherr"}.get(campaign, "Partner")
    if inserted:
        print(f"[outreach] +{inserted} {label} ({query})", flush=True)
    return inserted


def discover_batches(
    campaign: str = config.CAMPAIGN_PARTNER,
    max_batches: int | None = None,
) -> int:
    """Mehrere Discovery-Durchläufe pro Zyklus."""
    _, discover_limit, default_batches = _campaign_config(campaign)
    total = 0
    batches = max_batches or default_batches
    for _ in range(batches):
        n = discover_batch(campaign)
        total += n
        if n == 0:
            break
        if storage.get_counter("discovered", campaign) >= discover_limit:
            break
    return total


def discover_all_campaigns() -> int:
    total = discover_batches(config.CAMPAIGN_PARTNER)
    if config.REFERRAL_ENABLED:
        total += discover_batches(config.CAMPAIGN_REFERRAL)
    if config.BAUHERR_ENABLED:
        total += discover_batches(config.CAMPAIGN_BAUHERR)
    return total


def _advance_cursor(
    trade_idx: int,
    city_idx: int,
    token: str | None,
    trade_count: int,
    campaign: str,
) -> None:
    if token:
        storage.set_search_cursor(trade_idx, city_idx, token, campaign)
        return
    city_idx += 1
    if city_idx >= len(config.GERMAN_CITIES):
        city_idx = 0
        trade_idx += 1
    storage.set_search_cursor(trade_idx, city_idx, None, campaign)
