"""Hintergrund-Check der Betriebe, bevor sie dem Auftraggeber vorgeschlagen werden."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from places_api import lookup_ratings

from outreach import config
from outreach import storage


def is_reputable(rating: float | None, rating_count: int, business_status: str = "") -> bool:
    """Ein Betrieb fällt nur bei belastbar schlechtem Ruf durch."""
    if business_status == "CLOSED_PERMANENTLY":
        return False
    if rating is None:
        return True
    if rating_count < config.PROJEKT_MIN_RATING_COUNT:
        return True
    return rating >= config.PROJEKT_MIN_RATING


def quality_label(rating: float | None, rating_count: int) -> str:
    if rating is None:
        return "keine Google-Bewertung"
    stars = f"{rating:.1f}".replace(".", ",")
    if rating_count == 1:
        return f"{stars} Sterne (1 Bewertung)"
    return f"{stars} Sterne ({rating_count} Bewertungen)"


def backfill_ratings(campaign: str = config.CAMPAIGN_PROJEKT, limit: int = 10) -> int:
    """Holt Bewertungen für versandbereite Betriebe, die noch keine haben.

    Bewusst auf 'queued' begrenzt: nur Firmen, die tatsächlich angeschrieben
    werden, kosten einen Places-Aufruf.
    """
    rows = storage.queued_without_rating(campaign, limit)
    checked = 0
    for row in rows:
        rating, count, _maps = lookup_ratings(row["company_name"], row["city"])
        storage.set_rating(row["id"], rating, count)
        checked += 1
        if rating is not None and not is_reputable(rating, count):
            print(
                f"[outreach] Aussortiert (Ruf): {row['company_name']} "
                f"· {quality_label(rating, count)}",
                flush=True,
            )
    return checked
