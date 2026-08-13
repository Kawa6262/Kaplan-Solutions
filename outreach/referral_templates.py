"""Referral-Outreach — Makler, Architekten, Projektentwickler (B2B)."""

from __future__ import annotations

import hashlib

from company_config import COMPANY
from outreach.email_layout import (
    ORANGE_LUX,
    TEXT,
    body_block,
    cta_sub_link,
    safe,
    text_footer,
    wrap_outreach_email,
)
from outreach.urls import partner_form_url, referral_bauherr_url

REGION_LABEL = COMPANY.get("region_label", "Berlin & DACH")


def _variant(company: str) -> int:
    return int(hashlib.md5(company.encode()).hexdigest(), 16) % 3


def build_subject(company: str, city: str) -> str:
    v = _variant(company)
    region = city or "Ihrer Region"
    short = company[:50] if company else "Ihr Unternehmen"
    if v == 0:
        return f"Kurze Anfrage — {short}"
    if v == 1:
        return f"Bauherren vermitteln ({region})"
    return f"Rückfrage an {short}"


def build_bodies(
    company: str,
    city: str,
    trade: str,
    recipient_email: str = "",
    prospect_id: int | None = None,
) -> tuple[str, str]:
    region = city or "Ihrer Region"
    trade_hint = trade.split()[0] if trade else "Immobilien"
    bauherr_url = referral_bauherr_url(prospect_id)
    partner_url = partner_form_url(prospect_id)

    text = f"""Sehr geehrte Damen und Herren,

wir wenden uns an {company}, weil Sie in {region} als {trade_hint} für Bauherren und Immobilienprojekte tätig sind.

Kaplan Solutions vermittelt Bauherren kostenlos an geprüfte Bauunternehmen im DACH-Raum. Wenn Ihre Mandanten oder Kunden ein passendes Bauunternehmen suchen, leiten Sie sie gern weiter:

→ Für Ihre Mandanten (kostenlos): {bauherr_url}

Sie möchten selbst Aufträge über unser Netzwerk? Partner werden:
→ {partner_url}

Für Bauherren und für Sie als Empfehlungspartner entstehen keine Gebühren.

Mit freundlichen Grüßen
Kaplan Solutions
{text_footer(recipient_email, "Geschäftliche Kontaktaufnahme gemäß § 7 Abs. 3 UWG (Immobilien- und Bauleistungen).")}
"""

    body_html = body_block(
        f'wir wenden uns an <strong style="color:{TEXT};">{safe(company)}</strong>, weil Sie in '
        f'<strong style="color:{TEXT};">{safe(region)}</strong> als {safe(trade_hint)} für Bauherren und Projekte tätig sind.',
        f"Kaplan Solutions vermittelt Bauherren <strong style=\"color:{TEXT};\">kostenlos</strong> an geprüfte Bauunternehmen "
        f"({REGION_LABEL}, deutschlandweit). Wenn Mandanten oder Kunden ein passendes Bauunternehmen suchen, "
        "leiten Sie sie gern an uns weiter — wir übernehmen Vorauswahl und Erstkontakt.",
        f'Für Sie als Empfehlungspartner entstehen <strong style="color:{TEXT};">keine Gebühren</strong>.',
    )

    html = wrap_outreach_email(
        headline=f"Bauherren-Vermittlung — {company}",
        eyebrow="Empfehlungspartner",
        body_html=body_html,
        cta_label="Link für Mandanten (kostenlos)",
        cta_url=bauherr_url,
        cta_color=ORANGE_LUX,
        cta_secondary_html=cta_sub_link(partner_url, "Selbst Partner werden →"),
        recipient_email=recipient_email,
        legal="Geschäftliche Kontaktaufnahme gemäß § 7 Abs. 3 UWG (Immobilien- und Bauleistungen).",
    )

    return text, html
