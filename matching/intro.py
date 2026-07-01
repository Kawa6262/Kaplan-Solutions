"""Intro-Mail bei Hot Match — automatisch wenn Partner-Vertrag unterschrieben."""

from __future__ import annotations

import base64
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from company_config import COMPANY, company_footer_text
from lead_followup.config import AGENT_NAME, REPLY_EMAIL
from matching.alert_store import intro_already_sent, mark_intro_sent
from mailer import send_email

try:
    from business_model.contract_document import render_partner_contract_html
except ImportError:
    render_partner_contract_html = None  # type: ignore

GOLD = "#b87333"
GREEN = "#0b3d2e"
TEXT = "#1a1a1a"
MUTED = "#666666"


def _safe(s: str) -> str:
    return (
        str(s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _partner_contract_signed(match: dict) -> bool:
    val = str(match.get("an_vertrag") or match.get("vertrag") or "").strip().lower()
    return val in ("ja", "yes", "1", "true")


def _build_contact_attachment(match: dict) -> dict:
    ag = match.get("ag_firma") or match.get("ag_name") or "Bauherr"
    an = match.get("an_firma") or match.get("an_name") or "Partner"
    html = f"""<!DOCTYPE html><html lang="de"><head><meta charset="utf-8">
<title>Vermittelter Kontakt — Kaplan Solutions</title></head>
<body style="font-family:Arial,sans-serif;line-height:1.6;color:#1a1a1a;max-width:640px;margin:24px">
<h1 style="color:#0b3d2e;font-size:20px">Anlage: Vermittelter Kontakt</h1>
<p><strong>Match-ID:</strong> {_safe(match.get('match_id',''))}<br>
<strong>Passung:</strong> {match.get('score',0)}%<br>
<strong>Datum:</strong> {datetime.now(ZoneInfo('Europe/Berlin')).strftime('%d.%m.%Y')}</p>
<h2>Bauherr / Auftraggeber</h2>
<p>{_safe(ag)}<br>{_safe(match.get('ag_name',''))}<br>
E-Mail: {_safe(match.get('ag_email',''))}<br>
Tel: {_safe(match.get('ag_phone','—'))}<br>
Ref: {_safe(match.get('ag_ref',''))}</p>
<h2>Partner-Unternehmen</h2>
<p>{_safe(an)}<br>
E-Mail: {_safe(match.get('an_email',''))}<br>
Tel: {_safe(match.get('an_phone','—'))}<br>
Ref: {_safe(match.get('an_ref',''))}</p>
<h2>Projekt</h2>
<p>Region: {_safe(match.get('stadt',''))}<br>
Gewerk: {_safe(match.get('branche',''))}<br>
Passungsgründe: {_safe(match.get('reasons',''))}</p>
<p style="font-size:12px;color:#888;margin-top:32px">{_safe(company_footer_text())}</p>
</body></html>"""
    return {
        "filename": f"Vermittelter-Kontakt-{match.get('ag_ref','')}.html",
        "content": base64.b64encode(html.encode("utf-8")).decode("ascii"),
    }


def build_intro_email(match: dict) -> tuple[str, str, str]:
    ag_name = (match.get("ag_name") or "").strip()
    greeting = (
        ag_name
        if ag_name.startswith(("Sehr", "Herr", "Frau"))
        else f"Sehr geehrte/r {ag_name}" if ag_name else "Sehr geehrte Damen und Herren"
    )
    partner = match.get("an_firma") or match.get("an_name") or "unser Partnerunternehmen"
    ref = match.get("ag_ref") or ""
    ref_line = f" (Anfrage-Nr. {ref})" if ref else ""
    subject = f"Projektintro — {partner} für Ihr Bauvorhaben{ref_line}"

    text = f"""{greeting},

wie besprochen stelle ich Ihnen hiermit {partner} als passenden Partner für Ihr Projekt vor.

Projekt: {match.get('stadt', '')} · {match.get('branche', '')}
Passung laut unserem Matching: {match.get('score', 0)}%

Bitte antworten Sie auf diese E-Mail, um einen Termin für ein gemeinsames Erstgespräch zu vereinbaren.
Im Anhang finden Sie die Anlage „Vermittelter Kontakt“ gemäß unserem Vermittlungsvertrag.

{f'Ihre Anfrage-Nr.: {ref}' + chr(10) if ref else ''}
Bei Rückfragen: {REPLY_EMAIL} · {COMPANY['phone']}

Mit freundlichen Grüßen

{AGENT_NAME}
{company_footer_text()}
"""
    inner = f"""
<tr><td style="padding:32px 40px 20px;border-bottom:1px solid #e8e8e8">
  <p style="margin:0;font-size:11px;letter-spacing:0.35em;text-transform:uppercase;color:{GOLD}">Kaplan Solutions · Projektintro</p>
  <p style="margin:12px 0 0;font-family:Georgia,serif;font-size:22px;color:{TEXT}">Partner-Vorstellung</p>
</td></tr>
<tr><td style="padding:32px 40px;font-size:15px;line-height:1.75;color:{MUTED}">
  <p style="margin:0 0 20px;color:{TEXT}">{_safe(greeting)},</p>
  <p style="margin:0 0 20px">hiermit stelle ich Ihnen <strong style="color:{TEXT}">{_safe(partner)}</strong> als passenden Partner für Ihr Bauvorhaben vor
  ({_safe(match.get('stadt',''))} · {_safe(match.get('branche',''))}, Passung {match.get('score',0)}%).</p>
  <p style="margin:0 0 24px">Bitte antworten Sie auf diese E-Mail, um einen Termin für ein <strong>gemeinsames Erstgespräch</strong> zu vereinbaren.
  Im Anhang: Anlage „Vermittelter Kontakt“.</p>
  {'<p style="margin:0 0 20px">Anfrage-Nr.: <strong style="color:' + GOLD + '">' + _safe(ref) + '</strong></p>' if ref else ''}
</td></tr>"""
    html = f"""<!DOCTYPE html><html lang="de"><body style="margin:0;background:#f5f5f5">
<table width="100%" cellspacing="0" cellpadding="0"><tr><td align="center" style="padding:24px">
<table width="640" style="max-width:640px;background:#fff;border:1px solid #e0e0e0">{inner}
<tr><td style="padding:20px 40px;background:#fafafa;font-size:12px;color:#888">{_safe(company_footer_text()).replace(chr(10), '<br>')}</td></tr>
</table></td></tr></table></body></html>"""
    return subject, text, html


def build_admin_draft_email(match: dict) -> tuple[str, str, str]:
    partner = match.get("an_firma") or match.get("an_name") or "Partner"
    subject = f"⏳ Intro wartet auf Vertrag — {partner} ↔ {match.get('ag_firma') or match.get('ag_name')}"
    _, intro_text, _ = build_intro_email(match)
    text = f"""Hot Match — Intro noch NICHT automatisch gesendet.

GRUND: Partner-Vertrag ist noch nicht als „Ja“ im CRM markiert.

NÄCHSTE SCHRITTE:
1. Mustervertrag an Partner senden (Anhang)
2. Nach Unterschrift: CRM → Vertrag = Ja
3. Intro wird beim nächsten Match-Alert automatisch gesendet
   ODER manuell: python -m matching.intro_runner send --match-id {match.get('match_id')}

INTRO-ENTWURF (zum Kopieren nach Vertragsunterschrift):
{'—' * 40}
{intro_text}
{'—' * 40}

Partner-Ref: {match.get('an_ref')}
Bauherr-Ref: {match.get('ag_ref')}
"""
    html = f"<pre style='font-family:Arial,sans-serif;white-space:pre-wrap'>{_safe(text)}</pre>"
    return subject, text, html


def _mark_crm_intro_sent(match: dict) -> None:
    try:
        from sheet_client import crm_update

        for ref in (match.get("an_ref"), match.get("ag_ref")):
            ref = str(ref or "").strip()
            if ref:
                crm_update(ref, {"intro_gesendet": "Ja", "stage": "Erstkontakt"})
    except Exception as exc:
        print(f"[intro] CRM-Update übersprungen: {exc}", flush=True)


def send_intro_for_match(match: dict, *, admin_email: str, force: bool = False) -> dict:
    """Intro automatisieren — mit Vertrags-Gate."""
    match_id = str(match.get("match_id") or "").strip()
    if not match_id:
        return {"ok": False, "error": "match_id fehlt"}
    if not force and intro_already_sent(match_id):
        return {"ok": True, "skipped": "intro_already_sent", "match_id": match_id}

    ag_email = (match.get("ag_email") or "").strip()
    an_email = (match.get("an_email") or "").strip()
    if not ag_email:
        return {"ok": False, "error": "ag_email fehlt"}

    attachments = [_build_contact_attachment(match)]
    if render_partner_contract_html and not _partner_contract_signed(match):
        attachments.append({
            "filename": "Kaplan-Solutions-Vermittlungsvertrag-Partner.html",
            "content": base64.b64encode(
                render_partner_contract_html().encode("utf-8")
            ).decode("ascii"),
        })

    if not _partner_contract_signed(match):
        subj, text, html = build_admin_draft_email(match)
        send_email(admin_email, subj, text, html, attachments=attachments)
        mark_intro_sent(match_id, status="draft")
        return {
            "ok": True,
            "match_id": match_id,
            "intro": "draft",
            "reason": "partner_vertrag_fehlt",
            "admin": admin_email,
        }

    if not an_email:
        return {"ok": False, "error": "an_email fehlt"}

    subj, text, html = build_intro_email(match)
    cc = os.getenv("INTRO_CC_ADMIN", "1").strip().lower() not in ("0", "false", "no")
    # Resend: send to bauherr, use reply_to; CC partner via separate field — Resend supports cc array
    # mailer send_email only supports single 'to' — extend or send with Resend directly

    from mailer import uses_resend, send_resend, RESEND_FROM

    if uses_resend():
        import json
        import urllib.request

        payload = {
            "from": RESEND_FROM,
            "to": [ag_email],
            "cc": [an_email],
            "bcc": [admin_email] if cc else [],
            "subject": subj,
            "html": html,
            "text": text,
            "reply_to": REPLY_EMAIL,
            "attachments": attachments,
        }
        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {os.getenv('RESEND_API_KEY', '').strip()}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (compatible; KaplanSolutions/1.0)",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status >= 300:
                raise RuntimeError(f"Resend HTTP {resp.status}")
    else:
        send_email(ag_email, subj, text, html, reply_to=REPLY_EMAIL, attachments=attachments)

    mark_intro_sent(match_id, status="sent")
    _mark_crm_intro_sent(match)
    print(
        f"[intro] ✓ Intro gesendet → {ag_email} (CC {an_email}) · Match {match_id}",
        flush=True,
    )
    return {
        "ok": True,
        "match_id": match_id,
        "intro": "sent",
        "bauherr": ag_email,
        "partner": an_email,
    }
