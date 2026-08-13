"""Vermittlungsvertrag per E-Mail an Lead senden."""

from __future__ import annotations

import base64
import re
from typing import Any

from business_model.contract_branding import (
    GOLD,
    GOLD_DARK,
    MUTED,
    SITE,
    TEXT,
    email_letterhead_html,
    logo_email_attachment,
)
from company_config import COMPANY, company_footer_text
from lead_followup.config import AGENT_NAME, REPLY_EMAIL
from lead_followup.template import _safe
from mailer import email_configured, send_email


def parse_netto_eur(val: Any) -> float:
    s = str(val or "").strip().replace("€", "").replace(" ", "")
    if not s:
        return 0.0
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif re.match(r"^\d{1,3}(\.\d{3})+$", s):
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return 0.0


def lead_payload_from_request(data: dict, lead: dict | None = None) -> dict:
    lead = lead or {}
    ref = (data.get("ref") or lead.get("ref") or "").strip()
    name = data.get("name") or lead.get("name", "")
    company = (
        data.get("firma")
        or data.get("company")
        or lead.get("company")
        or lead.get("firma")
        or lead.get("name")
        or name
    )
    if str(company).strip() in ("—", "-", ""):
        company = name
    merged = {**lead, **{k: v for k, v in data.items() if v not in (None, "")}}
    anschrift = (data.get("anschrift") or "").strip()
    if not anschrift:
        parts: list[str] = []
        seen: set[str] = set()
        for key in ("standort", "location", "region", "stadt", "plz"):
            val = str(merged.get(key) or "").strip()
            if val and val not in ("—", "-") and val.lower() not in seen:
                seen.add(val.lower())
                parts.append(val)
        anschrift = ", ".join(parts)
    return {
        "ref": ref,
        "name": name,
        "company": company,
        "firma": data.get("firma") or company,
        "email": data.get("email") or lead.get("email", ""),
        "telefon": data.get("telefon") or lead.get("telefon") or lead.get("phone", ""),
        "stadt": data.get("region") or data.get("stadt") or lead.get("stadt", ""),
        "plz": data.get("plz") or lead.get("plz", ""),
        "anschrift": anschrift,
        "rechtsform": data.get("rechtsform") or lead.get("rechtsform", ""),
        "vertretung": data.get("vertretung") or data.get("name") or lead.get("name", ""),
        "ust_id": data.get("ust_id") or lead.get("ust_id", ""),
        "role_type": lead.get("role_type") or ("bauherr" if data.get("type") == "bauherr" else "partner"),
    }


def resolve_contract_type(data: dict, lead: dict | None = None) -> str:
    lead = lead or {}
    contract_type = (data.get("type") or data.get("contract_type") or "").strip().lower()
    if not contract_type:
        contract_type = "bauherr" if lead.get("role_type") == "bauherr" else "partner"
    if contract_type == "partner" and lead.get("role_type") == "bauherr":
        contract_type = "bauherr"
    elif contract_type == "bauherr" and lead.get("role_type") == "partner":
        contract_type = "partner"
    return contract_type


def generate_contract_html(
    data: dict,
    lead: dict | None = None,
) -> tuple[str, str, dict | None]:
    from billing.provision import calculate_provision
    from business_model.contract_document import render_contract_html

    lead = lead or {}
    contract_type = resolve_contract_type(data, lead)
    payload = lead_payload_from_request(data, lead)
    netto_raw = data.get("netto_eur") or data.get("netto") or lead.get("netto") or lead.get("budget")
    netto = parse_netto_eur(netto_raw)
    project_ref = (data.get("project_ref") or data.get("projekt_ref") or "").strip()
    project_name = (data.get("project_name") or data.get("projekt_name") or "").strip()
    region = (data.get("region") or lead.get("stadt") or "").strip()
    ag_firma = (data.get("ag_firma") or data.get("auftraggeber") or "").strip()

    html_out = render_contract_html(
        contract_type,
        payload,
        netto_eur=netto if netto > 0 else None,
        project_ref=project_ref,
        project_name=project_name,
        region=region,
        ag_firma=ag_firma,
    )
    calc = calculate_provision(netto) if netto > 0 and contract_type == "partner" else None
    return html_out, contract_type, calc


def _greeting(name: str) -> str:
    name = (name or "").strip()
    if not name:
        return "Sehr geehrte Damen und Herren"
    if name.startswith(("Sehr", "Herr", "Frau")):
        return name
    return f"Sehr geehrte/r {name}"


def _transactional_email_wrap(body_html: str) -> str:
    letterhead = email_letterhead_html()
    return f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#eceae6">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#eceae6">
<tr><td align="center" style="padding:28px 16px 36px">
<table role="presentation" width="600" cellspacing="0" cellpadding="0"
  style="max-width:600px;width:100%;background:#ffffff;border:1px solid #ddd8cf;
  box-shadow:0 2px 8px rgba(0,0,0,.04)">
{letterhead}
{body_html}
<tr><td style="padding:18px 36px 26px;background:#faf9f7;border-top:1px solid #ebe8e2;
  font-family:Arial,Helvetica,sans-serif;font-size:11px;line-height:1.55;color:#888">
<p style="margin:0 0 4px;color:{GOLD_DARK};font-weight:600;letter-spacing:0.04em">Kaplan Solutions</p>
<p style="margin:0">{_safe(COMPANY['legal_name'])} · {_safe(COMPANY['street'])} · {_safe(COMPANY['zip_city'])}</p>
<p style="margin:8px 0 0"><a href="{SITE}" style="color:{GOLD};text-decoration:none">{SITE.replace('https://','')}</a></p>
</td></tr>
</table>
</td></tr>
</table>
</body></html>"""


def _professional_email_body(
    *,
    greeting: str,
    headline: str,
    paragraphs: list[str],
    attachment_label: str,
    ref: str,
    closing: str,
) -> str:
    body = "".join(
        f'<p style="margin:0 0 16px;color:{TEXT}">{_safe(p)}</p>' for p in paragraphs
    )
    ref_block = ""
    if ref:
        ref_block = (
            f'<p style="margin:0 0 16px;font-family:Arial,Helvetica,sans-serif;'
            f'font-size:13px;color:{MUTED}">Referenz: <span style="color:{GOLD}">{_safe(ref)}</span></p>'
        )
    return f"""<tr><td style="padding:28px 36px 8px">
  <p style="margin:0 0 6px;font-family:Georgia,'Times New Roman',serif;font-size:22px;
    font-weight:400;color:{GOLD_DARK};line-height:1.3">{_safe(headline)}</p>
</td></tr>
<tr><td style="padding:8px 36px 28px;font-family:Georgia,'Times New Roman',serif;
  font-size:15px;line-height:1.75;color:{TEXT}">
  <p style="margin:0 0 18px">{_safe(greeting)},</p>
  {body}
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
    style="margin:22px 0 20px;background:#f7f6f3;border:1px solid #e4dfd6">
    <tr><td style="padding:14px 18px;font-family:Arial,Helvetica,sans-serif;font-size:13px;line-height:1.5;color:{TEXT}">
      <span style="color:{MUTED}">Anhang:</span> {_safe(attachment_label)}
    </td></tr>
  </table>
  {ref_block}
  <p style="margin:0 0 4px">{_safe(closing)}</p>
  <p style="margin:18px 0 0;font-family:Georgia,'Times New Roman',serif;font-size:16px;color:{TEXT}">
    {_safe(AGENT_NAME)}</p>
  <p style="margin:4px 0 0;font-family:Arial,Helvetica,sans-serif;font-size:13px;color:{MUTED}">
    Kaplan Solutions · <a href="mailto:{_safe(REPLY_EMAIL)}" style="color:{GOLD};text-decoration:none">{_safe(REPLY_EMAIL)}</a>
    · {_safe(COMPANY['phone'])}
  </p>
</td></tr>"""


def build_contract_email(
    lead: dict,
    contract_type: str,
    calc: dict | None = None,
) -> tuple[str, str, str]:
    ref = (lead.get("ref") or "").strip()
    company = lead.get("company") or lead.get("firma") or lead.get("name") or "Ihr Unternehmen"
    greeting = _greeting(lead.get("name") or "")
    ref_tail = f" (Ref. {ref})" if ref else ""

    if contract_type == "bauherr":
        subject = f"Vermittlungsvertrag{ref_tail}"
        headline = "Ihr Vermittlungsvertrag"
        attachment_label = "Vermittlungsvertrag Bauherr (HTML)"
        paragraphs = [
            "anbei sende ich Ihnen unseren Vermittlungsvertrag.",
            (
                "Bitte öffnen Sie die Datei im Anhang, lesen Sie den Vertrag in Ruhe durch "
                "und senden Sie uns das unterschriebene Dokument per E-Mail zurück an "
                f"{REPLY_EMAIL}."
            ),
            (
                "Erst nach Eingang Ihrer Unterschrift können wir mit der Vermittlung passender "
                "Unternehmen für Ihr Projekt beginnen. Für Sie als Bauherr ist die Vermittlung "
                "ohne Berechnung."
            ),
        ]
    else:
        subject = f"Vermittlungsvertrag Partner{ref_tail}"
        headline = "Vermittlungsvertrag Partner"
        attachment_label = f"Vermittlungsvertrag — {company} (HTML)"
        paragraphs = [
            f"anbei sende ich Ihnen den Vermittlungsvertrag für {company}.",
            (
                "Bitte öffnen Sie die Datei im Anhang, lesen Sie den Vertrag durch und "
                "senden Sie uns das unterschriebene Dokument per E-Mail zurück an "
                f"{REPLY_EMAIL}."
            ),
            (
                "Mit Ihrer Unterschrift können wir Sie anschließend passenden Auftraggebern "
                "vorstellen und die Vermittlung aufnehmen. Alle vertraglichen Details "
                "stehen im Anhang."
            ),
        ]

    closing = "Mit freundlichen Grüßen"
    text = f"""{greeting},

{chr(10).join(paragraphs)}

Anhang: {attachment_label}
{f'Referenz: {ref}' + chr(10) if ref else ''}
{closing}

{AGENT_NAME}
Kaplan Solutions
{REPLY_EMAIL} · {COMPANY['phone']}

{company_footer_text()}
"""
    inner = _professional_email_body(
        greeting=greeting,
        headline=headline,
        paragraphs=paragraphs,
        attachment_label=attachment_label,
        ref=ref,
        closing=closing,
    )
    html = _transactional_email_wrap(inner)
    return subject, text, html


def contract_attachment(html: str, filename: str) -> dict:
    return {
        "filename": filename,
        "content": base64.b64encode(html.encode("utf-8")).decode("ascii"),
    }


def send_contract_to_lead(data: dict, lead: dict | None = None) -> dict:
    if not email_configured():
        return {"ok": False, "error": "E-Mail nicht konfiguriert (Resend/SMTP)"}

    lead = dict(lead or {})
    payload = lead_payload_from_request(data, lead)
    to_email = (payload.get("email") or "").strip()
    if not to_email or "@" not in to_email:
        return {"ok": False, "error": "Keine gültige E-Mail-Adresse beim Lead"}

    ref = payload.get("ref") or "Lead"
    html_contract, contract_type, calc = generate_contract_html(data, lead)
    subject, text, html = build_contract_email(payload, contract_type, calc)

    kind = "Partner" if contract_type == "partner" else "Bauherr"
    filename = f"Kaplan-Solutions-Vermittlungsvertrag-{kind}-{ref}.html"
    attachments = [contract_attachment(html_contract, filename)]
    logo_att = logo_email_attachment()
    if logo_att:
        attachments.insert(0, logo_att)

    send_email(
        to_email,
        subject,
        text,
        html,
        reply_to=REPLY_EMAIL,
        attachments=attachments,
        mail_kind="transactional",
        entity_ref=ref,
    )

    return {
        "ok": True,
        "to": to_email,
        "subject": subject,
        "filename": filename,
        "contract_type": contract_type,
        "provision": calc,
    }


def send_muster_contracts_to_admin() -> dict:
    """Vollständige Kunden-Mails (Partner + Bauherr) an Admin — inkl. Signatur-Links zum Testen."""
    from mailer import ADMIN_EMAIL

    if not email_configured() or not ADMIN_EMAIL:
        return {"ok": False, "error": "E-Mail nicht konfiguriert"}

    results = []
    demos = [
        {
            "type": "partner",
            "ref": "DEMO-PARTNER-01",
            "name": "Max Mustermann",
            "firma": "Muster Bau GmbH",
            "email": ADMIN_EMAIL,
            "netto_eur": 635000,
            "project_ref": "KS-2026-DU-01",
            "project_name": "MFH Sanierung Duisburg",
            "region": "Duisburg",
            "ag_firma": "Investor (vertraulich)",
        },
        {
            "type": "bauherr",
            "ref": "DEMO-BAUHERR-01",
            "name": "Lea Beispiel",
            "firma": "Beispiel Invest GmbH",
            "email": ADMIN_EMAIL,
            "project_ref": "KS-2026-DU-01",
            "project_name": "MFH Sanierung Duisburg",
            "region": "Duisburg",
        },
    ]
    for demo in demos:
        lead = {
            "ref": demo["ref"],
            "name": demo["name"],
            "company": demo["firma"],
            "firma": demo["firma"],
            "email": demo["email"],
            "role_type": demo["type"],
        }
        result = send_contract_to_lead(demo, lead)
        results.append({"type": demo["type"], **result})

    ok = all(r.get("ok") for r in results)
    return {
        "ok": ok,
        "to": ADMIN_EMAIL,
        "results": results,
        "note": "Zwei Test-Mails (Partner + Bauherr): schlichte Brief-Mail, Anhang = Vertrag, Rücksendung per E-Mail.",
    }
