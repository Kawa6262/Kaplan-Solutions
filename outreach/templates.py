"""Cold-Outreach E-Mail-Vorlagen (B2B, deutsch)."""

from __future__ import annotations

import hashlib

from company_config import COMPANY, company_footer_text
from email_deliverability import public_site_url, unsubscribe_url

SITE = public_site_url()
FORM_URL = f"{SITE}/#contact"
UNSUBSCRIBE_URL = unsubscribe_url()
REPLY = COMPANY.get("email", "kontakt@kaplan-solutions.de")
REGION_LABEL = COMPANY.get("region_label", "Berlin & DACH")

GOLD = "#c9a227"
GOLD_DIM = "#a88420"
TEXT = "#f5f5f5"
MUTED = "#b8b8b8"
BG = "#0a0a0a"
CARD = "#141414"
BORDER = "#2a2a2a"


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
    v = _variant(company)
    if v == 0:
        return f"Partnerschaft als {company} — qualifizierte Bauaufträge im DACH-Raum"
    if v == 1:
        return f"Neue Bauaufträge in {city or 'Ihrer Region'} — Kaplan Solutions"
    return f"Bauvermittlung: passende Projekte für {company}"


def build_bodies(company: str, city: str, trade: str) -> tuple[str, str]:
    region = city or "Ihrer Region"
    trade_hint = trade.split()[0] if trade else "Bau"

    text = f"""Sehr geehrte Damen und Herren,

wir wenden uns an {company}, weil Sie in {region} im Bereich {trade_hint} tätig sind und unserem Partnernetzwerk gut entsprechen könnten.

Kaplan Solutions ist eine spezialisierte Vermittlungsplattform für Bauaufträge im DACH-Raum. Wir bringen qualifizierte Bauherren und Investoren mit geprüften Bauunternehmen zusammen — persönlich, diskret und ohne versteckte Listengebühren.

WARUM KAPLAN SOLUTIONS?
• Qualifizierte Anfragen: Neubau, Sanierung, Gewerbe- und Wohnprojekte
• Seriositätsprüfung: Wir prüfen Partner und Projekte vor der Vermittlung
• Persönliche Betreuung: Ein fester Ansprechpartner begleitet den Prozess
• Regionale Ausrichtung: Schwerpunkt {REGION_LABEL} — deutschlandweit im DACH-Raum
• Transparente Konditionen: Keine Listengebühren — Erfolg durch erfolgreiche Vermittlung

SO LÄUFT EINE PARTNERSCHAFT AB
1. Sie stellen über unsere Website eine unverbindliche Anfrage (ca. 3 Minuten)
2. Wir melden uns zeitnah persönlich und besprechen Ihr Leistungsprofil
3. Bei Passung nehmen wir Sie in unser Partnernetzwerk auf und vermitteln passende Projekte

INTERESSE AN EINER PARTNERSCHAFT?
Bitte nutzen Sie ausschließlich unser Kontaktformular auf der Website:
{FORM_URL}

Wählen Sie dort „Ich suche Aufträge" und tragen Sie Ihre Firmendaten ein — wir melden uns zeitnah bei Ihnen.

Mit freundlichen Grüßen
Ihr Team von Kaplan Solutions

{company_footer_text()}
{SITE}

---
Diese Nachricht richtet sich an die geschäftliche Kontaktadresse von {company} im Zusammenhang mit Bauleistungen (§ 7 Abs. 3 UWG).
Widerspruch jederzeit unter {UNSUBSCRIBE_URL} oder per E-Mail an {REPLY} mit Betreff „Abmelden".
"""

    inner = f"""
<tr><td style="padding:0 40px 24px">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:linear-gradient(135deg,#1a1608 0%,#111 100%);border:1px solid {BORDER};border-radius:4px">
  <tr><td style="padding:28px 28px 8px;font-family:Georgia,serif;font-size:26px;line-height:1.25;color:{TEXT}">
    Qualifizierte Bauaufträge<br><span style="color:{GOLD}">für {_safe(company)}</span>
  </td></tr>
  <tr><td style="padding:0 28px 24px;font-family:Arial,Helvetica,sans-serif;font-size:14px;line-height:1.7;color:{MUTED}">
    Speziell für Unternehmen im Bereich <strong style="color:{TEXT}">{_safe(trade_hint)}</strong> in <strong style="color:{TEXT}">{_safe(region)}</strong> — diskret vermittelt durch Kaplan Solutions.
  </td></tr>
  </table>
</td></tr>

<tr><td style="padding:0 40px 8px;font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.75;color:{MUTED}">
  <p style="margin:0 0 18px;color:{TEXT}">Sehr geehrte Damen und Herren,</p>
  <p style="margin:0 0 18px">wir sind <strong style="color:{TEXT}">Kaplan Solutions</strong> — Ihr Partner für die Vermittlung erstklassiger Bauunternehmen im DACH-Raum. Aktuell erweitern wir unser Netzwerk um zuverlässige Partner wie <strong style="color:{GOLD}">{_safe(company)}</strong>.</p>
  <p style="margin:0">Wir bringen Bauherren und Investoren mit geprüften Unternehmen zusammen — von der Erstberatung bis zum passenden Erstgespräch. Für Partner entstehen <strong style="color:{TEXT}">keine Listengebühren</strong>.</p>
</td></tr>

<tr><td style="padding:24px 40px 8px">
  <p style="margin:0 0 14px;font-family:Arial,sans-serif;font-size:11px;letter-spacing:0.16em;text-transform:uppercase;color:{GOLD}">Ihre Vorteile als Partner</p>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
  <tr>
    <td width="50%" valign="top" style="padding:0 8px 12px 0">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:{CARD};border:1px solid {BORDER}">
      <tr><td style="padding:18px 16px;font-family:Arial,sans-serif;font-size:13px;line-height:1.6;color:{MUTED}">
        <p style="margin:0 0 6px;color:{GOLD};font-size:18px">✦</p>
        <strong style="color:{TEXT}">Qualifizierte Anfragen</strong><br>
        Neubau, Sanierung, Gewerbe- und Wohnprojekte aus dem DACH-Raum.
      </td></tr></table>
    </td>
    <td width="50%" valign="top" style="padding:0 0 12px 8px">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:{CARD};border:1px solid {BORDER}">
      <tr><td style="padding:18px 16px;font-family:Arial,sans-serif;font-size:13px;line-height:1.6;color:{MUTED}">
        <p style="margin:0 0 6px;color:{GOLD};font-size:18px">✦</p>
        <strong style="color:{TEXT}">Seriositätsprüfung</strong><br>
        Partner und Projekte werden vor der Vermittlung sorgfältig geprüft.
      </td></tr></table>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top" style="padding:0 8px 0 0">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:{CARD};border:1px solid {BORDER}">
      <tr><td style="padding:18px 16px;font-family:Arial,sans-serif;font-size:13px;line-height:1.6;color:{MUTED}">
        <p style="margin:0 0 6px;color:{GOLD};font-size:18px">✦</p>
        <strong style="color:{TEXT}">Persönliche Betreuung</strong><br>
        Ein fester Ansprechpartner begleitet Sie durch den gesamten Prozess.
      </td></tr></table>
    </td>
    <td width="50%" valign="top" style="padding:0 0 0 8px">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:{CARD};border:1px solid {BORDER}">
      <tr><td style="padding:18px 16px;font-family:Arial,sans-serif;font-size:13px;line-height:1.6;color:{MUTED}">
        <p style="margin:0 0 6px;color:{GOLD};font-size:18px">✦</p>
        <strong style="color:{TEXT}">Transparent &amp; fair</strong><br>
        Keine versteckten Gebühren — Konditionen werden offen besprochen.
      </td></tr></table>
    </td>
  </tr>
  </table>
</td></tr>

<tr><td style="padding:16px 40px 8px">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:{CARD};border:1px solid {BORDER}">
  <tr><td style="padding:22px 24px;font-family:Arial,sans-serif">
    <p style="margin:0 0 16px;color:{GOLD};font-size:11px;letter-spacing:0.16em;text-transform:uppercase">So läuft die Partnerschaft ab</p>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
    <tr><td style="padding:0 0 12px;font-size:14px;line-height:1.65;color:{MUTED}">
      <span style="display:inline-block;width:24px;height:24px;line-height:24px;text-align:center;background:{GOLD};color:#111;font-weight:bold;font-size:12px;border-radius:50%;margin-right:10px">1</span>
      <strong style="color:{TEXT}">Anfrage über die Website</strong> — dauert ca. 3 Minuten
    </td></tr>
    <tr><td style="padding:0 0 12px;font-size:14px;line-height:1.65;color:{MUTED}">
      <span style="display:inline-block;width:24px;height:24px;line-height:24px;text-align:center;background:{GOLD};color:#111;font-weight:bold;font-size:12px;border-radius:50%;margin-right:10px">2</span>
      <strong style="color:{TEXT}">Persönliche Rückmeldung</strong> — wir besprechen Ihr Leistungsprofil
    </td></tr>
    <tr><td style="padding:0;font-size:14px;line-height:1.65;color:{MUTED}">
      <span style="display:inline-block;width:24px;height:24px;line-height:24px;text-align:center;background:{GOLD};color:#111;font-weight:bold;font-size:12px;border-radius:50%;margin-right:10px">3</span>
      <strong style="color:{TEXT}">Aufnahme ins Netzwerk</strong> — Vermittlung passender Projekte
    </td></tr>
    </table>
  </td></tr>
  </table>
</td></tr>

<tr><td style="padding:28px 40px 12px" align="center">
  <table role="presentation" cellspacing="0" cellpadding="0">
  <tr><td align="center" style="border-radius:4px;background:linear-gradient(135deg,{GOLD} 0%,{GOLD_DIM} 100%)">
    <a href="{_safe(FORM_URL)}" style="display:inline-block;padding:16px 36px;font-family:Arial,sans-serif;font-size:15px;font-weight:bold;color:#111;text-decoration:none;letter-spacing:0.04em">Partnerschaft anfragen →</a>
  </td></tr>
  </table>
  <p style="margin:14px 0 0;font-family:Arial,sans-serif;font-size:12px;line-height:1.6;color:#888;text-align:center">
    Bitte nur über unser Kontaktformular:<br>
    <a href="{_safe(FORM_URL)}" style="color:{GOLD};text-decoration:none">{_safe(FORM_URL.replace('https://', ''))}</a><br>
    Wählen Sie <strong style="color:{MUTED}">„Ich suche Aufträge"</strong> im Formular.
  </p>
</td></tr>

<tr><td style="padding:8px 40px 28px;font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.75;color:{MUTED}">
  <p style="margin:0;color:{TEXT}">Mit freundlichen Grüßen<br><strong>Kaplan Solutions</strong></p>
</td></tr>

<tr><td style="padding:0 40px 24px;font-family:Arial,Helvetica,sans-serif;font-size:11px;color:#888;line-height:1.55">
  Diese Nachricht richtet sich an die geschäftliche Kontaktadresse von {_safe(company)} im Zusammenhang mit Bauleistungen (§ 7 Abs. 3 UWG).
  Widerspruch jederzeit unter <a href="{_safe(UNSUBSCRIBE_URL)}" style="color:{GOLD}">Abmelden</a> oder per E-Mail an <a href="mailto:{_safe(REPLY)}?subject=Abmeldung" style="color:{GOLD}">{_safe(REPLY)}</a>.
</td></tr>
"""

    html = f"""<!DOCTYPE html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:{BG}">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:{BG}">
<tr><td align="center" style="padding:32px 16px">
<table role="presentation" width="600" cellspacing="0" cellpadding="0" style="background:#111;border:1px solid {BORDER};overflow:hidden">
<tr><td style="padding:32px 40px 12px;border-bottom:1px solid {BORDER}">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
  <tr>
    <td style="font-family:Georgia,serif;font-size:24px;color:{GOLD};letter-spacing:0.04em">Kaplan Solutions</td>
    <td align="right" style="font-family:Arial,sans-serif;font-size:10px;color:#666;letter-spacing:0.14em;text-transform:uppercase">Premium Bauvermittlung</td>
  </tr>
  </table>
</td></tr>
{inner}
<tr><td style="padding:20px 40px 32px;font-family:Arial,sans-serif;font-size:12px;color:#666;line-height:1.6;border-top:1px solid {BORDER}">
  {_safe(company_footer_text())}<br>
  <a href="{_safe(SITE)}" style="color:{GOLD};text-decoration:none">{_safe(SITE.replace('https://', ''))}</a>
</td></tr>
</table></td></tr></table></body></html>"""

    return text, html
