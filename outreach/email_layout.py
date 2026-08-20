"""Einheitliches Premium-E-Mail-Layout — Kaplan Solutions (Corporate Letterhead)."""

from __future__ import annotations

from company_config import COMPANY, company_footer_text
from email_deliverability import public_site_url, unsubscribe_url

SITE = public_site_url().rstrip("/")
HERO_URL = f"{SITE}/assets/hero.jpg"
REPLY = COMPANY.get("email", "kontakt@kaplan-solutions.de")

# Brand
BG_OUTER = "#5a5650"
BG_DARK = "#0a0a0a"
BG_FOOTER = "#0a0a0a"
BG_CONTENT = "#161616"  # dunkles Luxus-Grau
BORDER = "#2a2a2a"
GOLD = "#b87333"
ORANGE_LUX = "#c47a2e"  # luxuriöses Orange (Referral-CTA)
GREEN = "#0b3d2e"
TEXT = "#f5f5f5"
MUTED = "#a3a3a3"
LIGHT_RULE = "#2e2e2e"
TEXT_LIGHT = "#f5f5f5"
TEXT_DIM = "#8a8580"
HIGHLIGHT_BG = "#1f1f1f"

HERO_H = 72


def safe(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def postal_line() -> str:
    street = (COMPANY.get("street") or "").strip()
    zip_city = (COMPANY.get("zip_city") or "").strip()
    if street and not street.startswith("["):
        return f"{street}, {zip_city}"
    return zip_city or "Berlin"


def _dark_mode_guard() -> str:
    """Gmail/Apple Dark Mode: helle Bereiche und Masthead erzwingen."""
    return """
<style type="text/css">
  :root { color-scheme: light only; supported-color-schemes: light; }
  .email-card, .email-card td, .email-body, .email-body td,
  .email-head-block, .email-head-block td {
    background-color: #161616 !important;
  }
  .email-masthead, .email-masthead td { background-color: #0a0a0a !important; }
  .email-masthead-name { color: #f5f5f5 !important; }
  .email-masthead-sub { color: #b87333 !important; }
  .email-masthead-tag { color: #8a8580 !important; }
  .email-headline { color: #f5f5f5 !important; }
  .email-eyebrow { color: #b87333 !important; }
  .email-salutation { color: #f5f5f5 !important; }
  .email-copy { color: #a3a3a3 !important; }
  @media (prefers-color-scheme: dark) {
    .email-card, .email-card td, .email-body, .email-body td,
    .email-head-block, .email-head-block td { background-color: #161616 !important; }
    .email-masthead, .email-masthead td { background-color: #0a0a0a !important; }
    .email-masthead-name { color: #f5f5f5 !important; }
    .email-headline { color: #f5f5f5 !important; }
    .email-salutation { color: #f5f5f5 !important; }
    .email-copy { color: #a3a3a3 !important; }
  }
  u + .body .email-card { background-color: #161616 !important; }
</style>"""


def _brand_masthead() -> str:
    """Integrierte Markenzeile — Typografie wie Website, kein PNG."""
    return f"""
<table role="presentation" class="email-masthead" width="100%" cellspacing="0" cellpadding="0" border="0"
       bgcolor="{BG_DARK}" style="background:{BG_DARK};">
<tr>
  <td bgcolor="{BG_DARK}" style="background:{BG_DARK};padding:0;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
    <tr>
      <td width="3" bgcolor="{GOLD}" style="width:3px;background:{GOLD};font-size:0;line-height:0;">&nbsp;</td>
      <td style="padding:26px 48px 22px;">
        <a href="{safe(SITE)}" style="text-decoration:none;display:block;">
          <table role="presentation" cellspacing="0" cellpadding="0" border="0">
          <tr>
            <td style="vertical-align:baseline;padding-right:10px;">
              <span class="email-masthead-name"
                    style="font-family:Georgia,'Times New Roman',serif;font-size:32px;font-weight:400;
                           letter-spacing:-0.02em;color:{TEXT_LIGHT};line-height:1;">
                KAPLAN
              </span>
            </td>
            <td style="vertical-align:baseline;">
              <span class="email-masthead-sub"
                    style="font-family:Arial,Helvetica,sans-serif;font-size:10px;font-weight:600;
                           letter-spacing:0.38em;text-transform:uppercase;color:{GOLD};line-height:1;">
                Solutions
              </span>
            </td>
          </tr>
          </table>
          <p class="email-masthead-tag"
             style="margin:10px 0 0;font-family:Arial,Helvetica,sans-serif;font-size:10px;
                    font-weight:400;letter-spacing:0.24em;text-transform:uppercase;color:{TEXT_DIM};">
            Premium Bauvermittlung &middot; DACH
          </p>
        </a>
      </td>
    </tr>
    </table>
  </td>
</tr>
</table>"""


def wrap_outreach_email(
    *,
    headline: str,
    eyebrow: str,
    body_html: str,
    cta_label: str,
    cta_url: str,
    cta_secondary_html: str = "",
    recipient_email: str = "",
    legal: str = "Geschäftliche Kontaktaufnahme gemäß § 7 Abs. 3 UWG (Bauleistungen).",
    cta_color: str = GREEN,
) -> str:
    """Fester HTML-Rahmen — Hero, integrierter Masthead, Letterhead, Footer."""
    unsub = unsubscribe_url(recipient_email)
    postal = safe(postal_line())
    site_short = safe(SITE.replace("https://", ""))

    return f"""<!DOCTYPE html>
<html lang="de" xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="color-scheme" content="light only">
  <meta name="supported-color-schemes" content="light">
  <title>Kaplan Solutions</title>
  {_dark_mode_guard()}
</head>
<body class="body" style="margin:0;padding:0;background:{BG_OUTER};-webkit-text-size-adjust:100%;">
<table role="presentation" class="email-outer" width="100%" cellspacing="0" cellpadding="0" border="0"
       style="background:{BG_OUTER};padding:32px 16px;">
<tr><td align="center">

<table role="presentation" class="email-card" width="600" cellspacing="0" cellpadding="0" border="0"
       bgcolor="{BG_CONTENT}"
       style="max-width:600px;width:100%;background:{BG_CONTENT};border:1px solid {BORDER};border-collapse:collapse;">

<!-- Hero-Banner -->
<tr>
  <td style="padding:0;line-height:0;font-size:0;background:{BG_DARK};">
    <img src="{safe(HERO_URL)}" alt="" width="600" height="{HERO_H}"
         style="display:block;width:100%;max-width:600px;height:{HERO_H}px;object-fit:cover;
                object-position:center center;border:0;outline:none;text-decoration:none;">
  </td>
</tr>

<!-- Integrierter Marken-Masthead (Typografie, kein PNG) -->
<tr><td style="padding:0;">{_brand_masthead()}</td></tr>

<!-- Gold-Linie -->
<tr><td bgcolor="{GOLD}" style="height:2px;background:{GOLD};font-size:0;line-height:0;">&nbsp;</td></tr>

<!-- Überschrift -->
<tr>
  <td class="email-head-block" bgcolor="{BG_CONTENT}"
      style="background:{BG_CONTENT};padding:32px 48px 24px;">
    <table role="presentation" cellspacing="0" cellpadding="0" border="0">
    <tr>
      <td style="padding-right:12px;vertical-align:middle;">
        <table role="presentation" cellspacing="0" cellpadding="0" border="0">
        <tr><td style="width:28px;height:1px;background:{GOLD};font-size:0;line-height:0;">&nbsp;</td></tr>
        </table>
      </td>
      <td style="vertical-align:middle;">
        <p class="email-eyebrow"
           style="margin:0;font-family:Arial,Helvetica,sans-serif;font-size:11px;
                  font-weight:600;letter-spacing:0.22em;text-transform:uppercase;color:{GOLD};">
          {safe(eyebrow)}
        </p>
      </td>
    </tr>
    </table>
    <h1 class="email-headline"
        style="margin:14px 0 22px;font-family:Georgia,'Times New Roman',serif;font-size:24px;
               font-weight:400;line-height:1.4;color:{TEXT_LIGHT};">
      {safe(headline)}
    </h1>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
      <tr><td style="height:1px;background:{LIGHT_RULE};font-size:0;line-height:0;">&nbsp;</td></tr>
    </table>
  </td>
</tr>

<!-- Body -->
<tr>
  <td class="email-body" bgcolor="{BG_CONTENT}"
      style="background:{BG_CONTENT};padding:28px 48px 12px;
             font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.8;color:{MUTED};">
    {body_html}
  </td>
</tr>

<!-- CTA -->
<tr>
  <td bgcolor="{BG_CONTENT}" style="background:{BG_CONTENT};padding:12px 48px 36px;text-align:center;">
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center">
      <tr>
        <td bgcolor="{cta_color}" style="background:{cta_color};border-radius:2px;">
          <a href="{safe(cta_url)}"
             style="display:inline-block;padding:16px 36px;background:{cta_color};color:#ffffff;
                    font-family:Arial,Helvetica,sans-serif;font-size:14px;font-weight:600;
                    text-decoration:none;letter-spacing:0.04em;border-radius:2px;">
            {safe(cta_label)}
          </a>
        </td>
      </tr>
    </table>
    {cta_secondary_html}
  </td>
</tr>

<!-- Signatur -->
<tr>
  <td bgcolor="{BG_CONTENT}" style="background:{BG_CONTENT};padding:0 48px 36px;
             font-family:Arial,Helvetica,sans-serif;font-size:15px;color:{TEXT};">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
      <tr><td style="height:1px;background:{LIGHT_RULE};font-size:0;line-height:0;">&nbsp;</td></tr>
    </table>
    <p style="margin:20px 0 0;line-height:1.65;color:{MUTED};">Mit freundlichen Grüßen</p>
    <p style="margin:8px 0 0;font-family:Georgia,'Times New Roman',serif;font-size:17px;color:{GOLD};">
      Kaplan Solutions
    </p>
  </td>
</tr>

<!-- Footer -->
<tr>
  <td bgcolor="{BG_FOOTER}" style="background:{BG_FOOTER};padding:28px 48px;
             font-family:Arial,Helvetica,sans-serif;font-size:11px;line-height:1.7;color:#999999;">
    <p style="margin:0 0 14px;font-family:Georgia,'Times New Roman',serif;font-size:14px;color:#cccccc;">
      <span style="color:#f5f5f5;">KAPLAN</span>
      <span style="font-size:9px;letter-spacing:0.28em;color:{GOLD};text-transform:uppercase;"> Solutions</span>
    </p>
    <p style="margin:0 0 12px;color:#aaaaaa;">{safe(legal)}</p>
    <p style="margin:0 0 4px;">
      <a href="{safe(unsub)}" style="color:{GOLD};text-decoration:none;">Abmelden</a>
      &nbsp;&middot;&nbsp;
      <a href="mailto:{safe(REPLY)}?subject=Abmeldung" style="color:{GOLD};text-decoration:none;">{safe(REPLY)}</a>
      &nbsp;&middot;&nbsp;
      <a href="{safe(SITE)}" style="color:{GOLD};text-decoration:none;">{site_short}</a>
    </p>
    <p style="margin:10px 0 0;color:#666666;">{postal}</p>
  </td>
</tr>

</table>
</td></tr>
</table>
</body>
</html>"""


def body_block(*paragraphs: str) -> str:
    """Standard-Absätze mit Begrüßung."""
    parts = [
        f'<p class="email-salutation" style="margin:0 0 20px;color:{TEXT};'
        f'font-size:15px;">Sehr geehrte Damen und Herren,</p>'
    ]
    for p in paragraphs:
        parts.append(
            f'<p class="email-copy" style="margin:0 0 20px;color:{MUTED};">{p}</p>'
        )
    return "\n".join(parts)


def reply_hint_html() -> str:
    return (
        f'<p class="email-copy" style="margin:4px 0 0;font-size:13px;color:#888888;line-height:1.65;">'
        f'Oder antworten Sie einfach auf diese E-Mail mit '
        f'<strong style="color:{TEXT};font-weight:600;">„Interesse"</strong> '
        f"— wir melden uns persönlich.</p>"
    )


def website_lead_required_text(form_url: str) -> str:
    """Hinweis: Anfrage über die Website (mit Link)."""
    url = (form_url or f"{public_site_url().rstrip('/')}/#contact").strip()
    return (
        f"Bitte stellen Sie Ihre Anfrage über unsere Website — wir melden uns zeitnah persönlich:\n"
        f"{url}"
    )


def website_lead_required_html(form_url: str) -> str:
    url = (form_url or f"{public_site_url().rstrip('/')}/#contact").strip()
    return highlight_box(
        f'<strong style="color:{TEXT};">Anfrage über unsere Website</strong><br>'
        f"Bitte stellen Sie Ihre Anfrage bequem online — wir melden uns zeitnah persönlich bei Ihnen.<br>"
        f'<a href="{safe(url)}" style="color:{GOLD};text-decoration:none;font-weight:600;">'
        f"{safe(url)}</a>"
    )


def cta_sub_link(url: str, label: str) -> str:
    return (
        f'<p style="margin:18px 0 0;font-size:12px;color:#999999;text-align:center;line-height:1.6;">'
        f'<a href="{safe(url)}" style="color:{GOLD};text-decoration:none;font-weight:600;">'
        f"{safe(label)}</a></p>"
    )


def highlight_box(html: str) -> str:
    """Akzent-Box für Hinweise (Bauherr etc.)."""
    return f"""
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:4px 0 0;">
<tr>
  <td style="padding:18px 20px;background:{HIGHLIGHT_BG};border-left:3px solid {GOLD};
             font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.65;color:{MUTED};">
    {html}
  </td>
</tr>
</table>"""


def text_footer(recipient_email: str, legal: str) -> str:
    unsub = unsubscribe_url(recipient_email)
    return f"""
{company_footer_text()}
{SITE}

---
{legal}
Abmelden: {unsub}
oder Antwort an {REPLY} mit Betreff „Abmeldung"."""
