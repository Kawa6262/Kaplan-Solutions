"""Bauherr-Outreach — Projektentwickler, Bauträger, Ingenieurbüros (potenzielle Auftraggeber)."""

from __future__ import annotations

import hashlib

from outreach.email_layout import (
    TEXT,
    body_block,
    highlight_box,
    reply_hint_html,
    safe,
    text_footer,
    wrap_outreach_email,
)
from outreach.urls import bauherr_form_url


def _variant(company: str) -> int:
    return int(hashlib.md5(company.encode()).hexdigest(), 16) % 3


def build_subject(company: str, city: str) -> str:
    region = city or "Ihrer Region"
    v = _variant(company)
    short = company[:50] if company else "Ihr Unternehmen"
    if v == 0:
        return f"Anfrage zu Projekten in {region}"
    if v == 1:
        return f"Kurze Rückfrage — {short}"
    return f"Bauvermittlung ({region})"


def build_bodies(
    company: str,
    city: str,
    trade: str,
    recipient_email: str = "",
    prospect_id: int | None = None,
) -> tuple[str, str]:
    region = city or "Ihrer Region"
    trade_hint = trade or "Bauprojekt"
    form_url = bauherr_form_url(prospect_id)

    text = f"""Sehr geehrte Damen und Herren,

wir wenden uns an {company}, weil Sie in {region} im Bereich {trade_hint} tätig sind.

Kaplan Solutions vermittelt Bauherren und Projektverantwortliche kostenlos an geprüfte Bauunternehmen im DACH-Raum.

Haben Sie ein anstehendes Bau- oder Sanierungsprojekt?
→ Kostenlose Anfrage (2 Min.): {form_url}

Oder antworten Sie mit „Interesse" — wir melden uns persönlich.

Mit freundlichen Grüßen
Kaplan Solutions
{text_footer(recipient_email, "Geschäftliche Kontaktaufnahme gemäß § 7 Abs. 3 UWG (Bauleistungen).")}
"""

    highlight = highlight_box(
        "Haben Sie ein anstehendes Bau- oder Sanierungsprojekt?<br>"
        f'<span style="color:{TEXT};font-weight:600;">Wir vermitteln kostenlos an geprüfte Partner.</span>'
    )

    body_html = body_block(
        f'wir wenden uns an <strong style="color:{TEXT};">{safe(company)}</strong>, weil Sie in '
        f'<strong style="color:{TEXT};">{safe(region)}</strong> im Bereich {safe(trade_hint)} tätig sind.',
        "Kaplan Solutions vermittelt Bauherren und Projektverantwortliche "
        f'<strong style="color:{TEXT};">kostenlos</strong> an geprüfte Bauunternehmen, '
        "Handwerksbetriebe und Generalunternehmer im DACH-Raum.",
    ) + highlight + reply_hint_html()

    html = wrap_outreach_email(
        headline=f"Bauvermittlung — {company}",
        eyebrow="Auftraggeber",
        body_html=body_html,
        cta_label="Kostenlose Anfrage — 2 Min.",
        cta_url=form_url,
        recipient_email=recipient_email,
        legal="Geschäftliche Kontaktaufnahme gemäß § 7 Abs. 3 UWG (Bauleistungen).",
    )

    return text, html
