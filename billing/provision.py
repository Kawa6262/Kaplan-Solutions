"""Provisionsberechnung — 5 % netto, min/max aus provisions_config."""

from __future__ import annotations

from provisions_config import PROVISIONS


def _parse_eur(val: str) -> float:
    raw = str(val or "").strip().replace("€", "").replace(" ", "")
    raw = raw.replace(".", "").replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return 0.0


def _fmt_eur(amount: float) -> str:
    return f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def calculate_provision(netto_eur: float) -> dict:
    pct = float(str(PROVISIONS.get("partner_percent", "5")).replace(",", "."))
    min_e = _parse_eur(str(PROVISIONS.get("partner_min", "1500")))
    max_e = _parse_eur(str(PROVISIONS.get("partner_max", "35000")))
    netto = max(0.0, float(netto_eur))
    provision_net = max(min_e, min(max_e, netto * pct / 100.0))
    vat_rate = 0.19
    vat = round(provision_net * vat_rate, 2)
    gross = round(provision_net + vat, 2)
    return {
        "netto_order": netto,
        "provision_net": round(provision_net, 2),
        "vat_rate_pct": 19.0,
        "vat_amount": vat,
        "gross_total": gross,
        "percent": pct,
        "min_eur": min_e,
        "max_eur": max_e,
        "provision_net_fmt": _fmt_eur(provision_net),
        "vat_amount_fmt": _fmt_eur(vat),
        "gross_total_fmt": _fmt_eur(gross),
        "netto_order_fmt": _fmt_eur(netto),
    }
