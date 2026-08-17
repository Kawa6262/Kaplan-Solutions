"""Vermittlungsvertrag per E-Mail an Lead senden."""

from __future__ import annotations

import base64
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

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

TZ = ZoneInfo("Europe/Berlin")
SCHEDULED_PATH = Path(__file__).resolve().parent.parent / "data" / "contract_scheduled.json"


def _load_scheduled() -> dict:
    if not SCHEDULED_PATH.is_file():
        return {}
    try:
        data = json.loads(SCHEDULED_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_scheduled(data: dict) -> None:
    SCHEDULED_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULED_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


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
    highlight_html: str = "",
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
  {highlight_html}
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

    highlight_html = ""
    if contract_type == "bauherr":
        subject = f"Vermittlungsvertrag{ref_tail}"
        headline = "Ihr Vermittlungsvertrag"
        attachment_label = "Vermittlungsvertrag Bauherr (PDF)"
        highlight_html = (
            f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" '
            f'style="margin:0 0 20px;background:#faf8f3;border:1px solid {GOLD};'
            f'border-left:4px solid {GOLD}">'
            f'<tr><td style="padding:16px 18px;font-family:Arial,Helvetica,sans-serif;'
            f'font-size:14px;line-height:1.55;color:{TEXT}">'
            f'<strong style="color:{GOLD_DARK};font-size:15px;display:block;margin-bottom:6px">'
            f"Keine Kosten für Sie als Auftraggeber</strong>"
            f"Die Vermittlung ist für Sie <strong>kostenfrei</strong>. "
            f"Es fallen weder Vermittlungsgebühren noch sonstige Entgelte an — "
            f"<strong>auf Sie kommen keine Kosten zu</strong>."
            f"</td></tr></table>"
        )
        paragraphs = [
            "anbei erhalten Sie unseren Vermittlungsrahmenvertrag für Ihr Projekt als PDF.",
            (
                "Bitte öffnen Sie die PDF-Datei im Anhang (auch auf dem Smartphone), "
                "unterschreiben Sie den Vertrag und senden "
                f"uns das Dokument per E-Mail zurück an {REPLY_EMAIL}. "
                "Mit Ihrer Unterschrift bestätigen Sie die vertraglichen Rahmenbedingungen — "
                "erst danach beginnen wir mit der Vermittlung passender Unternehmen."
            ),
        ]
    else:
        subject = f"Vermittlungsvertrag Partner{ref_tail}"
        headline = "Vermittlungsvertrag Partner"
        attachment_label = f"Vermittlungsvertrag — {company} (PDF)"
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
    text_blocks = [f"{greeting},", ""]
    if contract_type == "bauherr":
        text_blocks.extend(
            [
                ">>> KEINE KOSTEN FÜR SIE ALS AUFTRAGGEBER <<<",
                (
                    "Die Vermittlung ist kostenfrei. Es fallen weder Vermittlungsgebühren "
                    "noch sonstige Entgelte an — auf Sie kommen keine Kosten zu."
                ),
                "",
            ]
        )
    text_blocks.extend(paragraphs)
    text_blocks.extend(
        [
            "",
            f"Anhang: {attachment_label}",
            *( [f"Referenz: {ref}"] if ref else [] ),
            "",
            closing,
            "",
            AGENT_NAME,
            "Kaplan Solutions",
            f"{REPLY_EMAIL} · {COMPANY['phone']}",
            "",
            company_footer_text(),
        ]
    )
    text = "\n".join(text_blocks)
    inner = _professional_email_body(
        greeting=greeting,
        headline=headline,
        paragraphs=paragraphs,
        attachment_label=attachment_label,
        ref=ref,
        closing=closing,
        highlight_html=highlight_html,
    )
    html = _transactional_email_wrap(inner)
    return subject, text, html


def contract_attachment(content: str | bytes, filename: str, *, binary: bool = False) -> dict:
    if binary:
        raw = content if isinstance(content, bytes) else content.encode("utf-8")
    else:
        raw = content.encode("utf-8") if isinstance(content, str) else content
    return {
        "filename": filename,
        "content": base64.b64encode(raw).decode("ascii"),
    }


def build_contract_attachments(
    html_contract: str,
    contract_type: str,
    ref: str,
) -> tuple[list[dict], str, str]:
    """PDF-Anhang (Handy-tauglich), sonst HTML-Fallback."""
    from business_model.contract_pdf import html_to_pdf_bytes, pdf_filename_for

    pdf_bytes, engine = html_to_pdf_bytes(html_contract)
    if pdf_bytes:
        filename = pdf_filename_for(contract_type, ref)
        return [contract_attachment(pdf_bytes, filename, binary=True)], filename, engine
    kind = "Partner" if contract_type == "partner" else "Bauherr"
    filename = f"Kaplan-Solutions-Vermittlungsvertrag-{kind}-{ref}.html"
    return [contract_attachment(html_contract, filename)], filename, ""


def _attach_contract_files(
    html_contract: str,
    contract_type: str,
    ref: str,
) -> tuple[list[dict], str, str]:
    attachments, filename, engine = build_contract_attachments(html_contract, contract_type, ref)
    logo_att = logo_email_attachment()
    if logo_att:
        attachments.insert(0, logo_att)
    return attachments, filename, engine


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

    attachments, filename, pdf_engine = _attach_contract_files(html_contract, contract_type, ref)

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
        "attachment_format": "pdf" if filename.endswith(".pdf") else "html",
        "pdf_engine": pdf_engine,
    }


def notify_admin_contract_sent(
    data: dict,
    lead: dict | None,
    result: dict,
    *,
    source: str = "manual",
) -> None:
    """Bestätigung an Admin nach manuellem Vertragsversand aus dem CRM."""
    from mailer import ADMIN_EMAIL

    if not email_configured() or not ADMIN_EMAIL:
        return
    lead = dict(lead or {})
    payload = lead_payload_from_request(data, lead)
    ref = payload.get("ref") or result.get("ref") or "—"
    company = payload.get("company") or payload.get("firma") or payload.get("name") or "Lead"
    to_email = result.get("to") or payload.get("email") or ""
    fmt = result.get("attachment_format") or ("pdf" if str(result.get("filename", "")).endswith(".pdf") else "html")
    subject = f"✓ Vertrag erfolgreich gesendet — {company} ({ref})"
    text = f"""Der Vertrag wurde erfolgreich versendet.

Empfänger: {payload.get('name', '')} · {company}
E-Mail: {to_email}
Referenz: {ref}
Anhang: {result.get('filename', '')} ({fmt})
Quelle: Kaplan Sales CRM ({source})

{company_footer_text()}
"""
    html = f"""<div style="font-family:Georgia,serif;font-size:15px;line-height:1.6;color:#222">
<p><strong>✓ Vertrag erfolgreich gesendet</strong></p>
<p>{_safe(payload.get('name', ''))} · {_safe(company)}<br>{_safe(to_email)}</p>
<p style="color:#666">Ref. {_safe(ref)} · {_safe(result.get('filename', ''))} ({_safe(fmt)})</p>
</div>"""
    try:
        send_email(
            ADMIN_EMAIL,
            subject,
            text,
            html,
            reply_to=REPLY_EMAIL,
            mail_kind="transactional",
            entity_ref=ref,
        )
    except Exception:
        pass


def schedule_contract_to_lead(
    data: dict,
    lead: dict | None = None,
    *,
    scheduled_for: datetime,
) -> dict:
    """Vertrag per Resend zu festem Zeitpunkt senden (z. B. 7:00 Bürozeit)."""
    from mailer import ADMIN_EMAIL, send_resend, uses_resend

    if not email_configured():
        return {"ok": False, "error": "E-Mail nicht konfiguriert (Resend/SMTP)"}
    if not uses_resend():
        return {"ok": False, "error": "Geplanter Versand erfordert Resend (scheduled_at)"}

    lead = dict(lead or {})
    payload = lead_payload_from_request({**data, "mark_sent": False}, lead)
    to_email = (payload.get("email") or "").strip()
    if not to_email or "@" not in to_email:
        return {"ok": False, "error": "Keine gültige E-Mail-Adresse beim Lead"}

    ref = payload.get("ref") or "Lead"
    scheduled = _load_scheduled()
    if ref in scheduled and not scheduled[ref].get("crm_done") and not data.get("replace_scheduled"):
        existing = scheduled[ref]
        return {
            "ok": True,
            "scheduled": True,
            "skipped": "already_scheduled",
            "scheduled_for": existing.get("scheduled_for"),
            "to": existing.get("to"),
        }
    if ref in scheduled and data.get("replace_scheduled"):
        from mailer import cancel_resend_email

        old_id = (scheduled.get(ref) or {}).get("resend_id")
        if old_id:
            cancel_resend_email(old_id)
        scheduled.pop(ref, None)
        _save_scheduled(scheduled)

    dt = scheduled_for
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    now = datetime.now(TZ)
    if dt <= now:
        return send_contract_to_lead({**data, "mark_sent": True}, lead)

    html_contract, contract_type, calc = generate_contract_html(data, lead)
    subject, text, html = build_contract_email(payload, contract_type, calc)

    attachments, filename, _pdf_engine = _attach_contract_files(html_contract, contract_type, ref)

    scheduled_at = dt.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        resend_id = send_resend(
            to_email,
            subject,
            text,
            html,
            reply_to=REPLY_EMAIL,
            attachments=attachments,
            scheduled_at=scheduled_at,
            mail_kind="transactional",
            entity_ref=ref,
        )
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

    company = payload.get("company") or payload.get("firma") or payload.get("name") or "Lead"
    scheduled[ref] = {
        "ref": ref,
        "to": to_email,
        "company": company,
        "name": payload.get("name", ""),
        "scheduled_for": dt.isoformat(timespec="seconds"),
        "resend_id": resend_id,
        "calc": calc,
        "crm_done": False,
        "filename": filename,
        "subject": subject,
    }
    _save_scheduled(scheduled)

    when_fmt = dt.strftime("%d.%m.%Y %H:%M")
    if ADMIN_EMAIL:
        admin_subject = f"Vertrag geplant — {company} ({ref}) · {when_fmt} Uhr"
        admin_text = f"""Vertrag für {company} ist geplant — noch nicht versendet.

Lead: {payload.get('name', '')} · {company}
E-Mail: {to_email}
Referenz: {ref}
Versand: {when_fmt} Uhr (Europe/Berlin)

Der Vertrag geht automatisch zur geplanten Zeit raus. CRM wird danach auf „Vertrag versendet“ gesetzt.

{company_footer_text()}
"""
        admin_html = f"""<div style="font-family:Georgia,serif;font-size:15px;line-height:1.6;color:#222">
<p><strong>Vertrag geplant — { _safe(company) }</strong></p>
<p>{ _safe(payload.get('name', '')) } · { _safe(to_email) } · Ref. { _safe(ref) }</p>
<p style="color:#666">Versand: <strong>{ _safe(when_fmt) } Uhr</strong></p>
</div>"""
        try:
            send_email(
                ADMIN_EMAIL,
                admin_subject,
                admin_text,
                admin_html,
                reply_to=REPLY_EMAIL,
                mail_kind="transactional",
                entity_ref=f"schedule-{ref}",
            )
        except Exception:
            pass

    return {
        "ok": True,
        "scheduled": True,
        "to": to_email,
        "subject": subject,
        "filename": filename,
        "contract_type": contract_type,
        "provision": calc,
        "scheduled_for": dt.isoformat(timespec="seconds"),
        "resend_id": resend_id,
    }


def finalize_due_scheduled_contracts() -> int:
    """CRM + Admin-Bestätigung nach geplantem Versandzeitpunkt."""
    from mailer import ADMIN_EMAIL

    scheduled = _load_scheduled()
    if not scheduled:
        return 0

    now = datetime.now(TZ)
    finalized = 0
    for ref, item in scheduled.items():
        if item.get("crm_done"):
            continue
        raw = item.get("scheduled_for") or ""
        try:
            sf = datetime.fromisoformat(raw)
        except ValueError:
            continue
        if sf.tzinfo is None:
            sf = sf.replace(tzinfo=TZ)
        if now < sf:
            continue

        from business_model.contract_auto import _crm_after_send, _mark_sent

        calc = item.get("calc")
        _crm_after_send(ref, calc)
        _mark_sent(ref, {"scheduled": True, "resend_id": item.get("resend_id")})
        item["crm_done"] = True
        finalized += 1

        if ADMIN_EMAIL:
            company = item.get("company") or ref
            subject = f"Vertrag versendet — {company} ({ref})"
            text = f"""Der geplante Vertrag wurde versendet.

Lead: {item.get('name', '')} · {company}
E-Mail: {item.get('to', '')}
Referenz: {ref}
Versandzeit: {sf.strftime('%d.%m.%Y %H:%M')} Uhr

{company_footer_text()}
"""
            html = f"""<div style="font-family:Georgia,serif;font-size:15px;line-height:1.6;color:#222">
<p><strong>Vertrag versendet (geplant)</strong></p>
<p>{_safe(item.get('name', ''))} · {_safe(company)}<br>{_safe(item.get('to', ''))}</p>
<p style="color:#666">Ref. {_safe(ref)} · {_safe(sf.strftime('%d.%m.%Y %H:%M'))} Uhr</p>
</div>"""
            try:
                send_email(
                    ADMIN_EMAIL,
                    subject,
                    text,
                    html,
                    reply_to=REPLY_EMAIL,
                    mail_kind="transactional",
                    entity_ref=ref,
                )
            except Exception:
                pass

    _save_scheduled(scheduled)
    return finalized


def send_contract_draft_to_admin(
    data: dict,
    lead: dict,
    *,
    note: str = "",
) -> dict:
    """Vertragsexakt wie an den Lead — zur Freigabe nur an Admin, nicht an den Lead."""
    from mailer import ADMIN_EMAIL

    if not email_configured() or not ADMIN_EMAIL:
        return {"ok": False, "error": "E-Mail nicht konfiguriert (Resend/SMTP + ADMIN_EMAIL)"}

    lead = dict(lead or {})
    payload = lead_payload_from_request({**data, "mark_sent": False}, lead)
    to_email = (payload.get("email") or "").strip()
    ref = payload.get("ref") or "Lead"
    company = payload.get("company") or payload.get("firma") or payload.get("name") or "Lead"

    html_contract, contract_type, calc = generate_contract_html(data, lead)
    subject, text, html = build_contract_email(payload, contract_type, calc)

    attachments, filename, pdf_engine = _attach_contract_files(html_contract, contract_type, ref)

    admin_subject = f"[ENTWURF] {subject} — {company} ({ref})"
    fmt_note = "PDF" if filename.endswith(".pdf") else "HTML"
    intro = (
        f"Entwurf zur Freigabe — noch nicht an {to_email or 'den Lead'} gesendet.\n\n"
        f"Lead: {company} · {payload.get('name', '')} · {ref}\n"
        f"Geplant an: {to_email}\n"
        f"Anhang: {filename} ({fmt_note}"
        f"{', ' + pdf_engine if pdf_engine else ''})\n"
    )
    if note:
        intro += f"\nAnfrage / Notiz:\n{note.strip()}\n"
    if calc:
        intro += (
            f"\nProvision (Plan): {calc.get('provision_net_fmt')} € netto "
            f"bei {calc.get('netto_order_fmt')} € Auftragsvolumen.\n"
        )
    intro += "\n--- So würde die Kunden-Mail aussehen ---\n\n"

    admin_text = intro + text
    note_html = (
        f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" '
        f'style="margin:0 0 20px;background:#fff8e6;border:1px solid #e8dcc8">'
        f'<tr><td style="padding:14px 18px;font-family:Arial,sans-serif;font-size:13px;'
        f'line-height:1.55;color:#5c4a32">'
        f"<strong>Entwurf — noch nicht versendet</strong><br>"
        f"Lead: {_safe(company)} · {_safe(payload.get('name', ''))} · {_safe(ref)}<br>"
        f"Geplant an: {_safe(to_email)}"
    )
    if note:
        note_html += f"<br><br><strong>Anfrage:</strong><br>{_safe(note.strip())}"
    if calc:
        note_html += (
            f"<br><br>Provision (Plan): {_safe(calc.get('provision_net_fmt', ''))} € netto "
            f"bei {_safe(calc.get('netto_order_fmt', ''))} € Auftragsvolumen."
        )
    note_html += "</td></tr></table>"
    customer_body_start = html.find('<tr><td style="padding:28px 36px 8px">')
    customer_part = html[customer_body_start:] if customer_body_start > 0 else html
    letterhead = email_letterhead_html()
    admin_html = f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#eceae6">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#eceae6">
<tr><td align="center" style="padding:28px 16px 36px">
<table role="presentation" width="600" cellspacing="0" cellpadding="0"
  style="max-width:600px;width:100%;background:#ffffff;border:1px solid #ddd8cf">
{letterhead}
{note_html}
{customer_part}
</table></td></tr></table></body></html>"""

    send_email(
        ADMIN_EMAIL,
        admin_subject,
        admin_text,
        admin_html,
        reply_to=REPLY_EMAIL,
        attachments=attachments,
        mail_kind="transactional",
        entity_ref=f"draft-{ref}",
    )

    return {
        "ok": True,
        "to": ADMIN_EMAIL,
        "lead_email": to_email,
        "subject": admin_subject,
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
