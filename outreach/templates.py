"""Cold-Outreach E-Mail-Vorlagen — Posteingang-optimiert (hell, kurz, B2B)."""

from __future__ import annotations

import hashlib

from company_config import COMPANY, company_footer_text
from email_deliverability import public_site_url, unsubscribe_url

SITE = public_site_url()
FORM_URL = f"{SITE}/#contact"
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
    """Kurze, sachliche Betreffzeilen — ohne Spam-Trigger."""
    v = _variant(company)
    region = city or "Ihrer Region"
    if v == 0:
        return f"Kaplan Solutions — Partnernetzwerk Bau ({region})"
    if v == 1:
        return f"Kurze Anfrage an {company}"
    return f"Bauvermittlung: Partneraufnahme {company}"


def build_bodies(
    company: str,
    city: str,
    trade: str,
    recipient_email: str = "",
) -> tuple[str, str]:
    region = city or "Ihrer Region"
    trade_hint = trade.split()[0] if trade else "Bau"
    unsub = unsubscribe_url(recipient_email)
    postal = _postal_line()

    text = f"""Sehr geehrte Damen und Herren,

wir wenden uns an {company}, weil Sie in {region} im Bereich {trade_hint} tätig sind.

Kaplan Solutions vermittelt qualifizierte Bauaufträge im DACH-Raum — persönlich, diskret und ohne Listengebühren für Partner. Wir prüfen Anfragen und Projekte vor der Vermittlung und koordinieren den Erstkontakt.

Interesse an einer unverbindlichen Partnerschaft?
Kontaktformular (ca. 3 Minuten): {FORM_URL}
Bitte „Ich suche Aufträge" wählen.

Mit freundlichen Grüßen
Kaplan Solutions

{company_footer_text()}
{SITE}

---
Geschäftliche Kontaktaufnahme gemäß § 7 Abs. 3 UWG (Bauleistungen).
Abmelden: {unsub}
oder Antwort an {REPLY} mit Betreff „Abmeldung".
"""

    inner = f"""
<tr><td style="padding:36px 40px 20px;border-bottom:1px solid #e8e8e8">
  <p style="margin:0 0 8px;font-family:Arial,Helvetica,sans-serif;font-size:10px;letter-spacing:0.35em;text-transform:uppercase;color:{GOLD}">Kaplan Solutions</p>
  <p style="margin:0;font-family:Georgia,'Times New Roman',serif;font-size:24px;color:{GREEN};font-weight:400;line-height:1.35">
    Partnernetzwerk Bau — {_safe(company)}
  </p>
</td></tr>

<tr><td style="padding:28px 40px;font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.75;color:{MUTED}">
  <p style="margin:0 0 18px;color:{TEXT}">Sehr geehrte Damen und Herren,</p>
  <p style="margin:0 0 18px">
    wir wenden uns an <strong style="color:{TEXT}">{_safe(company)}</strong>, weil Sie in
    <strong style="color:{TEXT}">{_safe(region)}</strong> im Bereich {_safe(trade_hint)} tätig sind.
  </p>
  <p style="margin:0 0 18px">
    Kaplan Solutions vermittelt qualifizierte Bauaufträge ({REGION_LABEL}, deutschlandweit).
    Für Partner entstehen <strong style="color:{TEXT}">keine Listengebühren</strong> — Vergütung nur bei erfolgreicher Vermittlung.
  </p>
  <p style="margin:0">
    Bei Interesse freuen wir uns über eine kurze Anfrage über unser Kontaktformular.
  </p>
</td></tr>

<tr><td style="padding:8px 40px 32px" align="center">
  <a href="{_safe(FORM_URL)}" style="display:inline-block;padding:14px 28px;background:{GREEN};color:#ffffff;font-family:Arial,sans-serif;font-size:14px;font-weight:600;text-decoration:none;border-radius:2px">
    Unverbindlich anfragen
  </a>
  <p style="margin:14px 0 0;font-size:12px;color:#999;text-align:center;line-height:1.5">
    Formular: „Ich suche Aufträge" wählen<br>
    <a href="{_safe(FORM_URL)}" style="color:{GOLD};text-decoration:none">{_safe(FORM_URL.replace('https://', ''))}</a>
  </p>
</td></tr>

<tr><td style="padding:0 40px 28px;font-family:Arial,Helvetica,sans-serif;font-size:15px;color:{TEXT}">
  <p style="margin:0">Mit freundlichen Grüßen<br><strong>Kaplan Solutions</strong></p>
</td></tr>

<tr><td style="padding:20px 40px;background:#fafafa;border-top:1px solid #e8e8e8;font-family:Arial,sans-serif;font-size:11px;color:#888;line-height:1.6">
  <p style="margin:0 0 8px">Geschäftliche Kontaktaufnahme gemäß § 7 Abs. 3 UWG (Bauleistungen).</p>
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
