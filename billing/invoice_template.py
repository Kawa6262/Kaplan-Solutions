"""HTML-Rechnung für Partner-Provision."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from company_config import COMPANY, company_footer_text


def _safe(s: str) -> str:
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_invoice(
    *,
    invoice_no: str,
    partner_name: str,
    partner_company: str,
    partner_email: str,
    ref: str,
    project_desc: str,
    amounts: dict,
    due_days: int = 14,
) -> tuple[str, str, str]:
    today = datetime.now(ZoneInfo("Europe/Berlin"))
    date_label = today.strftime("%d.%m.%Y")
    due_label = (today + __import__("datetime").timedelta(days=due_days)).strftime("%d.%m.%Y")
    brand = COMPANY.get("brand", "Kaplan Solutions")
    subject = f"Rechnung {invoice_no} — Vermittlungsprovision · {partner_company or partner_name}"

    text = f"""{brand}
Rechnung {invoice_no}
Datum: {date_label} · Fällig: {due_label}

Rechnungsempfänger:
{partner_company or partner_name}
{partner_email}

Leistung: Erfolgsprovision Vermittlung gemäß Vermittlungsvertrag
Anfrage-Nr.: {ref}
Projekt: {project_desc}

Auftragssumme (netto):     {amounts['netto_order_fmt']} €
Provision ({amounts['percent']:.1f} % netto): {amounts['provision_net_fmt']} €
zzgl. 19 % USt:           {amounts['vat_amount_fmt']} €
─────────────────────────
Rechnungsbetrag:          {amounts['gross_total_fmt']} €

Zahlungsziel: {due_days} Tage ohne Abzug.

{company_footer_text()}
"""
    html = f"""<!DOCTYPE html><html lang="de"><head><meta charset="utf-8"></head>
<body style="margin:0;font-family:Arial,sans-serif;color:#1a1a1a;background:#f5f5f5">
<table width="100%" cellspacing="0" cellpadding="0"><tr><td align="center" style="padding:32px 16px">
<table width="640" style="max-width:640px;background:#fff;border:1px solid #ddd">
<tr><td style="padding:32px 40px;background:#0b3d2e;color:#fff">
  <p style="margin:0;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:#c9a227">{_safe(brand)}</p>
  <p style="margin:8px 0 0;font-family:Georgia,serif;font-size:26px">Rechnung { _safe(invoice_no) }</p>
  <p style="margin:8px 0 0;font-size:13px;color:#c8d4ce">Datum {date_label} · Fällig {due_label}</p>
</td></tr>
<tr><td style="padding:32px 40px">
  <p style="margin:0 0 4px;font-size:11px;text-transform:uppercase;color:#888">Rechnungsempfänger</p>
  <p style="margin:0 0 24px"><strong>{_safe(partner_company or partner_name)}</strong><br>{_safe(partner_email)}</p>
  <table width="100%" style="border-collapse:collapse;font-size:14px">
    <tr style="background:#f7f7f7"><td colspan="2" style="padding:10px 12px;font-weight:bold">Leistungsbeschreibung</td></tr>
    <tr><td style="padding:10px 12px;border-bottom:1px solid #eee;width:40%">Leistung</td>
        <td style="padding:10px 12px;border-bottom:1px solid #eee">Erfolgsprovision Vermittlung (Vermittlungsvertrag)</td></tr>
    <tr><td style="padding:10px 12px;border-bottom:1px solid #eee">Anfrage-Nr.</td>
        <td style="padding:10px 12px;border-bottom:1px solid #eee"><strong style="color:#b87333">{_safe(ref)}</strong></td></tr>
    <tr><td style="padding:10px 12px;border-bottom:1px solid #eee">Projekt</td>
        <td style="padding:10px 12px;border-bottom:1px solid #eee">{_safe(project_desc)}</td></tr>
    <tr><td style="padding:10px 12px;border-bottom:1px solid #eee">Auftragssumme (netto)</td>
        <td style="padding:10px 12px;border-bottom:1px solid #eee;text-align:right">{amounts['netto_order_fmt']} €</td></tr>
    <tr><td style="padding:10px 12px;border-bottom:1px solid #eee">Provision ({amounts['percent']:.1f} % netto)</td>
        <td style="padding:10px 12px;border-bottom:1px solid #eee;text-align:right"><strong>{amounts['provision_net_fmt']} €</strong></td></tr>
    <tr><td style="padding:10px 12px;border-bottom:1px solid #eee">zzgl. 19 % USt</td>
        <td style="padding:10px 12px;border-bottom:1px solid #eee;text-align:right">{amounts['vat_amount_fmt']} €</td></tr>
    <tr style="background:#e8f5e9"><td style="padding:14px 12px;font-weight:bold">Rechnungsbetrag</td>
        <td style="padding:14px 12px;text-align:right;font-size:18px;font-weight:bold;color:#0b3d2e">{amounts['gross_total_fmt']} €</td></tr>
  </table>
  <p style="margin:24px 0 0;font-size:13px;color:#666">Zahlungsziel: {due_days} Tage netto ohne Abzug.</p>
</td></tr>
<tr><td style="padding:20px 40px;background:#fafafa;font-size:11px;color:#888;border-top:1px solid #eee">
  {_safe(company_footer_text()).replace(chr(10), '<br>')}
</td></tr>
</table></td></tr></table></body></html>"""
    return subject, text, html
