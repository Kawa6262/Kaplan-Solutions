"""Professionelle Follow-up-E-Mails — persönlicher Agent-Ton."""

from __future__ import annotations

from company_config import COMPANY, company_footer_text
from lead_followup.config import AGENT_NAME, REPLY_EMAIL

GOLD = "#b87333"
TEXT = "#1a1a1a"
MUTED = "#666666"


def _safe(s: str) -> str:
    return (
        str(s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _email_wrap(inner_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f0f0f0">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f0f0f0;padding:32px 16px">
<tr><td align="center">
<table role="presentation" width="600" cellspacing="0" cellpadding="0" style="max-width:600px;width:100%;background:#ffffff">
{inner_html}
</table>
</td></tr>
</table>
</body></html>"""


def _role_body(role: str, name: str, company: str) -> tuple[str, str]:
    """Returns (headline, main_paragraphs_html/text content as tuple of strings for text)."""
    if role == "bauherr":
        headline = "Wir suchen passende Partner für Ihr Projekt"
        p1 = (
            "Ihre Anfrage haben wir in unsere aktive Vermittlungsliste aufgenommen. "
            "Unser Team prüft derzeit passende Bauunternehmen und Partner in Ihrer Region — "
            "qualifiziert, verfügbar und passend zu Ihrem Vorhaben."
        )
        p2 = (
            "Sobald wir einen geeigneten Partner identifiziert haben, melden wir uns "
            "persönlich bei Ihnen und koordinieren das Erstgespräch. "
            "Bis dahin arbeiten wir im Hintergrund für Sie."
        )
    else:
        company_label = company if company and company != "—" else "Ihr Unternehmen"
        headline = f"{company_label} ist in unserem Partnernetzwerk"
        p1 = (
            f"Wir haben {company_label} in unsere aktive Partnerliste aufgenommen. "
            "Unser Team gleicht Ihr Profil laufend mit qualifizierten Projektanfragen ab — "
            "regional passend und zu Ihren Gewerken."
        )
        p2 = (
            "Sobald eine passende Anfrage vorliegt, setzen wir uns persönlich mit Ihnen in Verbindung "
            "und besprechen die nächsten Schritte. Für die Zusammenarbeit senden wir Ihnen vor dem "
            "ersten Projektintro unseren Vermittlungsvertrag zur Unterzeichnung — "
            "erfolgsbasiert, ohne Vorabkosten."
        )
    return headline, p1, p2


def build_followup(data: dict) -> tuple[str, str, str]:
    name = (data.get("name") or "").strip() or "Sehr geehrte Damen und Herren"
    ref = (data.get("ref") or "").strip()
    role = (data.get("role") or "").strip()
    company = (data.get("company_name") or data.get("company") or "").strip()

    greeting = name if name.startswith(("Sehr", "Herr", "Frau")) else f"Sehr geehrte/r {name}"
    headline, p1, p2 = _role_body(role, name, company)

    ref_line = f" (Anfrage-Nr. {ref})" if ref else ""
    subject = f"Ihre Anfrage bei Kaplan Solutions — Wir sind für Sie da{ref_line}"

    text_body = f"""{greeting},

vielen Dank nochmals für Ihr Vertrauen in Kaplan Solutions.

{p1}

{p2}

{f'Ihre Anfrage-Nr.: {ref}' + chr(10) if ref else ''}
Bei Rückfragen erreichen Sie uns jederzeit:
E-Mail: {REPLY_EMAIL}
Telefon: {COMPANY['phone']}

Mit freundlichen Grüßen

{AGENT_NAME}
{company_footer_text()}

—
Kaplan Solutions · Vermittlung qualifizierter Bauaufträge
{COMPANY.get('website', 'https://kaplan-solutions.de')}
"""

    ref_html = (
        f'<p style="margin:0 0 24px;font-size:14px;color:{MUTED}">'
        f'Anfrage-Nr.: <strong style="color:{GOLD}">{_safe(ref)}</strong></p>'
        if ref
        else ""
    )

    inner = f"""<tr><td style="padding:40px 40px 24px;border-bottom:1px solid #e8e8e8">
  <p style="margin:0 0 16px;font-family:Arial,Helvetica,sans-serif;font-size:11px;letter-spacing:0.35em;text-transform:uppercase;color:{GOLD}">Kaplan Solutions</p>
  <p style="margin:0;font-family:Georgia,'Times New Roman',serif;font-size:26px;font-weight:400;color:{TEXT};line-height:1.35">{_safe(headline)}</p>
</td></tr>
<tr><td style="padding:32px 40px;font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.75;color:{MUTED}">
  <p style="margin:0 0 20px;color:{TEXT}">{_safe(greeting)},</p>
  <p style="margin:0 0 20px">vielen Dank nochmals für Ihr Vertrauen in <strong style="color:{TEXT}">Kaplan Solutions</strong>.</p>
  <p style="margin:0 0 20px">{_safe(p1)}</p>
  <p style="margin:0 0 28px">{_safe(p2)}</p>
  {ref_html}
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f7f7f7;border:1px solid #ebebeb;margin-bottom:28px">
  <tr><td style="padding:20px 24px">
    <p style="margin:0 0 8px;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:{GOLD}">Nächster Schritt</p>
    <p style="margin:0;font-size:14px;color:{TEXT}">Wir melden uns persönlich, sobald ein passender Partner gefunden wurde.</p>
  </td></tr>
  </table>
  <p style="margin:0 0 8px;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:#999999">Ihr Ansprechpartner</p>
  <p style="margin:0 0 4px;font-family:Georgia,'Times New Roman',serif;font-size:17px;color:{TEXT}">{_safe(AGENT_NAME)}</p>
  <p style="margin:0;font-size:14px;color:{MUTED}">
    E-Mail: <a href="mailto:{_safe(REPLY_EMAIL)}" style="color:{GOLD};text-decoration:none">{_safe(REPLY_EMAIL)}</a><br>
    Telefon: <span style="color:{TEXT}">{_safe(COMPANY['phone'])}</span>
  </p>
</td></tr>
<tr><td style="padding:0 40px 40px;font-family:Arial,Helvetica,sans-serif;font-size:12px;color:#aaaaaa;line-height:1.5;border-top:1px solid #e8e8e8">
  <p style="margin:24px 0 0">{_safe(company_footer_text()).replace(chr(10), '<br>')}</p>
</td></tr>"""

    return subject, text_body, _email_wrap(inner)
