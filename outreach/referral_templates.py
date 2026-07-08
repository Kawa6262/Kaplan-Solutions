"""Referral-Outreach — Makler, Architekten, Projektentwickler (B2B)."""

from __future__ import annotations

import hashlib

from company_config import COMPANY, company_footer_text
from email_deliverability import public_site_url, unsubscribe_url
from outreach.urls import partner_form_url, referral_bauherr_url

SITE = public_site_url()
REPLY = COMPANY.get("email", "kontakt@kaplan-solutions.de")
REGION_LABEL = COMPANY.get("region_label", "Berlin & DACH")

GOLD = "#b87333"
TEXT = "#1a1a1a"
MUTED = "#666666"
GREEN = "#0b3d2e"


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


def _postal_line() -> str:
    street = (COMPANY.get("street") or "").strip()
    zip_city = (COMPANY.get("zip_city") or "").strip()
    if street and not street.startswith("["):
        return f"{street}, {zip_city}"
    return zip_city or "Berlin"


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
    unsub = unsubscribe_url(recipient_email)
    postal = _postal_line()
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

{company_footer_text()}
{SITE}

---
Geschäftliche Kontaktaufnahme gemäß § 7 Abs. 3 UWG (Immobilien- und Bauleistungen).
Abmelden: {unsub}
oder Antwort an {REPLY} mit Betreff „Abmeldung".
"""

    inner = f"""
<tr><td style="padding:36px 40px 20px;border-bottom:1px solid #e8e8e8">
  <p style="margin:0 0 8px;font-family:Arial,Helvetica,sans-serif;font-size:10px;letter-spacing:0.35em;text-transform:uppercase;color:{GOLD}">Kaplan Solutions</p>
  <p style="margin:0;font-family:Georgia,'Times New Roman',serif;font-size:24px;color:{GREEN};font-weight:400;line-height:1.35">
    Bauherren-Vermittlung — {_safe(company)}
  </p>
</td></tr>

<tr><td style="padding:28px 40px;font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.75;color:{MUTED}">
  <p style="margin:0 0 18px;color:{TEXT}">Sehr geehrte Damen und Herren,</p>
  <p style="margin:0 0 18px">
    wir wenden uns an <strong style="color:{TEXT}">{_safe(company)}</strong>, weil Sie in
    <strong style="color:{TEXT}">{_safe(region)}</strong> als {_safe(trade_hint)} für Bauherren und Projekte tätig sind.
  </p>
  <p style="margin:0 0 18px">
    Kaplan Solutions vermittelt Bauherren <strong style="color:{TEXT}">kostenlos</strong> an geprüfte Bauunternehmen
    ({REGION_LABEL}, deutschlandweit). Wenn Mandanten oder Kunden ein passendes Bauunternehmen suchen,
    leiten Sie sie gern an uns weiter — wir übernehmen Vorauswahl und Erstkontakt.
  </p>
  <p style="margin:0">
    Für Sie als Empfehlungspartner entstehen <strong style="color:{TEXT}">keine Gebühren</strong>.
  </p>
</td></tr>

<tr><td style="padding:8px 40px 32px" align="center">
  <a href="{_safe(bauherr_url)}" style="display:inline-block;padding:14px 28px;background:{GREEN};color:#ffffff;font-family:Arial,sans-serif;font-size:14px;font-weight:600;text-decoration:none;border-radius:2px">
    Link für Mandanten (kostenlos)
  </a>
  <p style="margin:14px 0 0;font-size:12px;color:#999;text-align:center;line-height:1.5">
    <a href="{_safe(partner_url)}" style="color:{GOLD};text-decoration:none">Selbst Partner werden →</a>
  </p>
</td></tr>

<tr><td style="padding:0 40px 28px;font-family:Arial,Helvetica,sans-serif;font-size:15px;color:{TEXT}">
  <p style="margin:0">Mit freundlichen Grüßen<br><strong>Kaplan Solutions</strong></p>
</td></tr>

<tr><td style="padding:20px 40px;background:#fafafa;border-top:1px solid #e8e8e8;font-family:Arial,sans-serif;font-size:11px;color:#888;line-height:1.6">
  <p style="margin:0 0 8px">Geschäftliche Kontaktaufnahme gemäß § 7 Abs. 3 UWG (Immobilien- und Bauleistungen).</p>
  <p style="margin:0">
    <a href="{_safe(unsub)}" style="color:{GOLD}">Abmelden</a>
    &nbsp;·&nbsp;
    <a href="mailto:{_safe(REPLY)}?subject=Abmeldung" style="color:{GOLD}">{_safe(REPLY)}</a>
  </p>
  <p style="margin:12px 0 0">{_safe(postal)} · {_safe(SITE.replace('https://', ''))}</p>
</td></tr>
"""

    html = f"""<!DOCTYPE html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f0f0f0">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f0f0f0;padding:28px 12px">
<tr><td align="center">
<table role="presentation" width="600" cellspacing="0" cellpadding="0" style="max-width:600px;width:100%;background:#ffffff;border:1px solid #e0e0e0">
{inner}
</table>
</td></tr>
</table>
</body></html>"""

    return text, html
