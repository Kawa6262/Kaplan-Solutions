"""Cold-Outreach E-Mail-Vorlagen — Partner (Auftragnehmer)."""

from __future__ import annotations

import hashlib

from company_config import COMPANY
from outreach.email_layout import (
    TEXT,
    body_block,
    cta_sub_link,
    reply_hint_html,
    safe,
    text_footer,
    wrap_outreach_email,
)
from outreach.urls import partner_form_url

REGION_LABEL = COMPANY.get("region_label", "Berlin & DACH")


def _variant(company: str) -> int:
    return int(hashlib.md5(company.encode()).hexdigest(), 16) % 3


def build_subject(company: str, city: str) -> str:
    """Sachliche Betreffzeilen — wie persönliche B2B-Mail, ohne Marketing-Trigger."""
    v = _variant(company)
    region = city or "Ihrer Region"
    short = company[:50] if company else "Ihr Unternehmen"
    if v == 0:
        return f"Kurze Anfrage — {short}"
    if v == 1:
        return f"Zusammenarbeit Bau ({region})"
    return f"Rückfrage an {short}"


def build_bodies(
    company: str,
    city: str,
    trade: str,
    recipient_email: str = "",
    prospect_id: int | None = None,
) -> tuple[str, str]:
    region = city or "Ihrer Region"
    trade_hint = trade.split()[0] if trade else "Bau"
    form_url = partner_form_url(prospect_id)

    text = f"""Sehr geehrte Damen und Herren,

wir wenden uns an {company}, weil Sie in {region} im Bereich {trade_hint} tätig sind.

Kaplan Solutions vermittelt qualifizierte Bauaufträge im DACH-Raum — persönlich, diskret und ohne Listengebühren für Partner. Wir prüfen Anfragen und Projekte vor der Vermittlung und koordinieren den Erstkontakt.

Interesse an einer unverbindlichen Partnerschaft?
→ Partner werden (ca. 2 Minuten): {form_url}
Das Formular ist bereits auf „Ich suche Aufträge" voreingestellt.

Noch einfacher: Antworten Sie auf diese E-Mail mit „Interesse" — wir melden uns persönlich.

Mit freundlichen Grüßen
Kaplan Solutions
{text_footer(recipient_email, "Geschäftliche Kontaktaufnahme gemäß § 7 Abs. 3 UWG (Bauleistungen).")}
"""

    body_html = body_block(
        f'wir wenden uns an <strong style="color:{TEXT};">{safe(company)}</strong>, weil Sie in '
        f'<strong style="color:{TEXT};">{safe(region)}</strong> im Bereich {safe(trade_hint)} tätig sind.',
        f"Kaplan Solutions vermittelt qualifizierte Bauaufträge ({REGION_LABEL}, deutschlandweit). "
        f'Für Partner entstehen <strong style="color:{TEXT};">keine Listengebühren</strong> — '
        f"Vergütung nur bei erfolgreicher Vermittlung.",
        f'Bei Interesse: <strong style="color:{TEXT};">Partner werden in 2 Minuten</strong> — '
        "Formular ist voreingestellt.",
    ) + reply_hint_html()

    html = wrap_outreach_email(
        headline=f"Partnernetzwerk Bau — {company}",
        eyebrow="Partnernetzwerk",
        body_html=body_html,
        cta_label="Partner werden — 2 Min.",
        cta_url=form_url,
        cta_secondary_html=cta_sub_link(form_url, 'Voreingestellt: „Ich suche Aufträge"'),
        recipient_email=recipient_email,
        legal="Geschäftliche Kontaktaufnahme gemäß § 7 Abs. 3 UWG (Bauleistungen).",
    )

    return text, html
