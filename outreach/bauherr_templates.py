"""Bauherr-Outreach — Projektentwickler, Bauträger, Ingenieurbüros (potenzielle Auftraggeber)."""

from __future__ import annotations

import hashlib

from company_config import COMPANY, company_footer_text
from email_deliverability import public_site_url, unsubscribe_url
from outreach.urls import bauherr_form_url

SITE = public_site_url()
REPLY = COMPANY.get("email", "kontakt@kaplan-solutions.de")


def _safe(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


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
    unsub = unsubscribe_url(recipient_email)
    form_url = bauherr_form_url(prospect_id)

    text = f"""Sehr geehrte Damen und Herren,

wir wenden uns an {company}, weil Sie in {region} im Bereich {trade_hint} tätig sind.

Kaplan Solutions vermittelt Bauherren und Projektverantwortliche kostenlos an geprüfte Bauunternehmen im DACH-Raum.

Haben Sie ein anstehendes Bau- oder Sanierungsprojekt?
→ Kostenlose Anfrage (2 Min.): {form_url}

Oder antworten Sie mit „Interesse" — wir melden uns persönlich.

Mit freundlichen Grüßen
Kaplan Solutions

{company_footer_text()}
{SITE}

Abmelden: {unsub}
"""

    html = f"""<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#1a1a1a;line-height:1.55;max-width:600px">
<p>Sehr geehrte Damen und Herren,</p>
<p>wir wenden uns an <strong>{_safe(company)}</strong>, weil Sie in <strong>{_safe(region)}</strong> im Bereich {_safe(trade_hint)} tätig sind.</p>
<p>Kaplan Solutions vermittelt Bauherren und Projektverantwortliche <strong>kostenlos</strong> an geprüfte Bauunternehmen, Handwerksbetriebe und Generalunternehmer im DACH-Raum.</p>
<p style="background:#f5f5f5;padding:14px;border-left:4px solid #b87333">Haben Sie ein anstehendes Bau- oder Sanierungsprojekt?<br/>
<a href="{_safe(form_url)}" style="color:#0b3d2e;font-weight:700">→ Kostenlose Anfrage (2 Min.)</a></p>
<p style="font-size:14px;color:#666">Oder auf diese E-Mail mit <strong>„Interesse"</strong> antworten.</p>
<p>Mit freundlichen Grüßen<br/>Kaplan Solutions</p>
<p style="font-size:11px;color:#888">{_safe(company_footer_text())}<br/>
<a href="{unsub}" style="color:#888">Abmelden</a></p>
</body></html>"""

    return text, html
