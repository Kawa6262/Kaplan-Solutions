"""Outreach-Dashboard — Live-Kennzahlen für Kaplan Sales CRM."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from outreach import config, storage

TZ = ZoneInfo("Europe/Berlin")

_CAMPAIGN_LABELS = {
    config.CAMPAIGN_PROJEKT: "Projekt-Ausschreibung",
    "partner": "Partner-Outreach",
    "referral": "Empfehlungen",
    "bauherr": "Bauherren",
}


def _today_iso() -> str:
    return datetime.now(TZ).strftime("%Y-%m-%d")


def _daily_limit(campaign: str) -> int:
    if campaign == config.CAMPAIGN_PROJEKT:
        return config.PROJEKT_DAILY_SEND_LIMIT
    if campaign == "referral":
        return int(getattr(config, "REFERRAL_DAILY_SEND_LIMIT", 0) or 0)
    if campaign == "bauherr":
        return int(getattr(config, "BAUHERR_DAILY_SEND_LIMIT", 0) or 0)
    return config.DAILY_SEND_LIMIT


def _send_enabled(campaign: str) -> bool:
    if campaign == config.CAMPAIGN_PROJEKT:
        return config.PROJEKT_SEND_ENABLED
    if campaign == "referral":
        return getattr(config, "REFERRAL_SEND_ENABLED", False)
    if campaign == "bauherr":
        return getattr(config, "BAUHERR_SEND_ENABLED", False)
    return config.DAILY_SEND_LIMIT > 0


def _projekt_meta() -> dict | None:
    if not config.PROJEKT_ENABLED:
        return None
    try:
        from outreach.projekt import AKTUELL

        if not AKTUELL.aktiv:
            return None
        return {
            "referenz": AKTUELL.referenz,
            "titel": AKTUELL.titel,
            "region": AKTUELL.region,
            "cities": list(config.PROJEKT_CITIES),
            "trades": len(config.PROJEKT_TRADE_QUERIES),
        }
    except Exception:
        return None


def _window_info() -> dict:
    try:
        from outreach import reliability

        now = datetime.now(TZ)
        return {
            "active": reliability.in_send_window_now(),
            "status": reliability.window_status_line(),
            "weekdays_only": config.SEND_WEEKDAYS_ONLY,
            "hour_start": config.SEND_HOUR_START,
            "hour_end": config.SEND_HOUR_END,
            "now": now.strftime("%d.%m.%Y %H:%M"),
        }
    except Exception:
        now = datetime.now(TZ)
        return {
            "active": False,
            "status": now.strftime("%H:%M"),
            "weekdays_only": config.SEND_WEEKDAYS_ONLY,
            "hour_start": config.SEND_HOUR_START,
            "hour_end": config.SEND_HOUR_END,
            "now": now.strftime("%d.%m.%Y %H:%M"),
        }


def gather_dashboard(
    *,
    campaign: str | None = None,
    day: str | None = None,
    sends_limit: int = 1000,
    sends_offset: int = 0,
    source: str = "local",
) -> dict:
    """Vollständiges Dashboard-Payload für CRM / Live-Sync."""
    storage.init_db()
    day = (day or _today_iso()).strip()
    filter_day = None if day == "all" else day
    summary = storage.stats_summary()
    campaigns = storage.campaign_stats()

    for key, row in campaigns.items():
        limit = _daily_limit(key)
        today_sent = int(row.get("today_sent") or 0)
        row["label"] = _CAMPAIGN_LABELS.get(key, key)
        row["daily_limit"] = limit
        row["remaining_today"] = max(0, limit - today_sent) if limit > 0 else 0
        row["send_enabled"] = _send_enabled(key)
        row["pending_total"] = int(row.get("queued") or 0) + int(row.get("new_with_email") or 0)

    sends, sends_total = storage.list_sends(
        campaign=None if campaign in (None, "", "all") else campaign,
        day=filter_day,
        limit=sends_limit,
        offset=sends_offset,
    )

    replies = storage.reply_stats(campaign if campaign not in (None, "", "all") else None)
    camp_filter = campaign if campaign not in (None, "", "all") else None

    return {
        "ok": True,
        "source": source,
        "updated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "day": day,
        "campaign_filter": campaign or "all",
        "summary": summary,
        "campaigns": campaigns,
        "projekt": _projekt_meta(),
        "window": _window_info(),
        "replies": replies,
        "sends": sends,
        "sends_total": sends_total,
        "sends_limit": sends_limit,
        "sends_offset": sends_offset,
        "by_city": storage.sent_breakdown_by_city(filter_day, campaign=camp_filter),
        "by_trade": storage.sent_breakdown_by_trade(filter_day, campaign=camp_filter),
        "unsubscribes": storage.unsubscribe_count(),
    }
