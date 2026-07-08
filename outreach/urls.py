"""Trackbare Kurzlinks für Outreach-Mails (UTM + Prospect-ID)."""

from __future__ import annotations

from urllib.parse import urlencode

from email_deliverability import public_site_url


def tracked_url(
    path: str,
    campaign: str,
    prospect_id: int | None = None,
    **extra: str,
) -> str:
    site = public_site_url().rstrip("/")
    params: dict[str, str] = {
        "utm_source": "outreach",
        "utm_medium": "email",
        "utm_campaign": campaign,
    }
    if prospect_id is not None:
        params["utm_content"] = f"p{prospect_id}"
    params.update({k: v for k, v in extra.items() if v})
    qs = urlencode(params)
    if path.startswith("/?"):
        return f"{site}{path}&{qs}" if "?" in path else f"{site}{path}?{qs}"
    return f"{site}{path}?{qs}"


def partner_form_url(prospect_id: int | None = None) -> str:
    """Direkt zum Formular (role=unternehmen) — funktioniert auch ohne /partner-Deploy."""
    site = public_site_url().rstrip("/")
    params: dict[str, str] = {
        "role": "unternehmen",
        "utm_source": "outreach",
        "utm_medium": "email",
        "utm_campaign": "partner_cold",
    }
    if prospect_id is not None:
        params["utm_content"] = f"p{prospect_id}"
    return f"{site}/?{urlencode(params)}#contact"


def referral_bauherr_url(prospect_id: int | None = None) -> str:
    return tracked_url("/empfehlung", "referral_cold", prospect_id)


def bauherr_form_url(prospect_id: int | None = None) -> str:
    return tracked_url("/kostenlos", "bauherr_cold", prospect_id)
