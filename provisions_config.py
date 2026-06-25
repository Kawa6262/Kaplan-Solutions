"""Provisions- und Konditionsmodell — zentral konfigurierbar via .env."""

from __future__ import annotations

import os


def _pct(key: str, default: str) -> str:
    return os.getenv(key, default).strip().replace(",", ".")


def _eur(key: str, default: str) -> str:
    raw = os.getenv(key, default).strip().replace(".", "").replace(",", ".")
    try:
        return f"{float(raw):,.0f}".replace(",", ".")
    except ValueError:
        return default


# Partner-Unternehmen (Auftragnehmer) — Hauptvergütung
PARTNER_PROVISION_PERCENT = _pct("PROVISION_PARTNER_PERCENT", "5.0")
PARTNER_PROVISION_MIN_EUR = _eur("PROVISION_PARTNER_MIN_EUR", "1500")
PARTNER_PROVISION_MAX_EUR = _eur("PROVISION_PARTNER_MAX_EUR", "35000")
PARTNER_NACHVERTRAGLICH_MONTHS = os.getenv("PROVISION_PARTNER_FOLLOWUP_MONTHS", "12").strip()

# Bauherren / Investoren — attraktiv: in der Regel kostenfrei
BAUHERR_PROVISION_PERCENT = _pct("PROVISION_BAUHERR_PERCENT", "0")
BAUHERR_PROVISION_MIN_EUR = _eur("PROVISION_BAUHERR_MIN_EUR", "0")

# Beratungspauschale (optional, nur wenn ausdrücklich vereinbart)
BERATUNGSPAUSCHALE_EUR = _eur("PROVISION_BERATUNG_EUR", "0")

PROVISIONS = {
    "partner_percent": PARTNER_PROVISION_PERCENT,
    "partner_min": PARTNER_PROVISION_MIN_EUR,
    "partner_max": PARTNER_PROVISION_MAX_EUR,
    "partner_followup_months": PARTNER_NACHVERTRAGLICH_MONTHS,
    "bauherr_percent": BAUHERR_PROVISION_PERCENT,
    "bauherr_min": BAUHERR_PROVISION_MIN_EUR,
    "beratung_eur": BERATUNGSPAUSCHALE_EUR,
}
