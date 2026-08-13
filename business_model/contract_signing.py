"""Digitale Vertragsunterschrift — Token, Speicherung, Admin-Benachrichtigung."""

from __future__ import annotations

import base64
import json
import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from company_config import COMPANY, company_footer_text
from lead_followup.config import AGENT_NAME, REPLY_EMAIL
from mailer import ADMIN_EMAIL, email_configured, send_email

TZ = ZoneInfo("Europe/Berlin")
BASE_DIR = Path(__file__).resolve().parent.parent
TOKENS_DIR = BASE_DIR / "data" / "contract_sign_tokens"
SIGNED_DIR = BASE_DIR / "data" / "signed_contracts"
TOKEN_TTL_DAYS = int(os.getenv("CONTRACT_SIGN_TTL_DAYS", "21"))


def _now_iso() -> str:
    return datetime.now(TZ).strftime("%Y-%m-%dT%H:%M:%S%z")


def _sign_secret() -> str:
    return (
        os.getenv("CONTRACT_SIGN_SECRET", "").strip()
        or os.getenv("ADMIN_CRM_SECRET", "").strip()
        or "dev-insecure-change-me"
    )


def create_signing_token(
    ref: str,
    contract_type: str,
    contract_data: dict,
    lead: dict,
) -> str:
    TOKENS_DIR.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(32)
    payload = {
        "token": token,
        "ref": ref,
        "contract_type": contract_type,
        "contract_data": contract_data,
        "lead_name": lead.get("name") or "",
        "lead_company": lead.get("company") or lead.get("firma") or "",
        "lead_email": lead.get("email") or "",
        "created_at": _now_iso(),
        "expires_at": (datetime.now(TZ) + timedelta(days=TOKEN_TTL_DAYS)).strftime("%Y-%m-%d"),
        "signed": False,
    }
    (TOKENS_DIR / f"{token}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return token


def load_signing_session(token: str) -> dict | None:
    token = (token or "").strip()
    if not token or "/" in token or ".." in token:
        return None
    path = TOKENS_DIR / f"{token}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if data.get("signed"):
        return {**data, "already_signed": True}
    exp = str(data.get("expires_at") or "")
    if exp:
        try:
            if datetime.strptime(exp, "%Y-%m-%d").date() < datetime.now(TZ).date():
                return None
        except ValueError:
            pass
    return data


def signed_document_url(token: str) -> str:
    site = os.getenv("COMPANY_WEBSITE", "https://kaplan-solutions.de").rstrip("/")
    return f"{site}/vertrag/unterschrieben/{token}"


def read_signed_document_html(token: str) -> str | None:
    path = TOKENS_DIR / f"{token}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not data.get("signed"):
        return None
    inline = data.get("signed_html")
    if isinstance(inline, str) and inline.strip():
        return inline
    b64 = data.get("signed_html_b64")
    if b64:
        try:
            return base64.b64decode(b64).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            pass
    fpath = Path(str(data.get("signed_file") or ""))
    if fpath.is_file():
        return fpath.read_text(encoding="utf-8")
    return None


def signing_url(token: str) -> str:
    site = os.getenv("COMPANY_WEBSITE", "https://kaplan-solutions.de").rstrip("/")
    return f"{site}/vertrag/unterschreiben/{token}"


def _embed_signature(html: str, *, name: str, ort: str, datum: str, sig_b64: str) -> str:
    sig_img = f'<img src="{sig_b64}" alt="Unterschrift" style="max-height:48px;max-width:180px" />'
    party_label = "Partner-Unternehmen" if "Partner" in html else "Auftraggeber"
    block = f"""
<div class="sig-block signed-block">
  <div class="sig-space">{sig_img}</div>
  <p class="sig-label"><strong>{name}</strong><br />{party_label} · {ort}, {datum}</p>
</div>"""
    if "Kaplan Solutions)</p>" in html:
        html = html.replace(
            "<p class=\"sig-label\">{{ c.legal_name }}",
            f"<p class=\"sig-label\"><strong>{COMPANY.get('legal_name','Kaplan Solutions')}</strong>",
            1,
        )
    # Replace first empty partner/auftraggeber sig block
    marker = '<div class="sig-space"></div>'
    idx = html.rfind(marker)
    if idx >= 0:
        html = html[:idx] + f'<div class="sig-space">{sig_img}</div>' + html[idx + len(marker):]
        html = html.replace(
            "(vertretungsberechtigt)</p>",
            f"<strong>{name}</strong><br />{ort}, {datum}</p>",
            1,
        )
    return html


def complete_signing(
    token: str,
    *,
    signer_name: str,
    ort: str,
    datum: str,
    signature_data_url: str,
    accept: bool,
) -> dict:
    session = load_signing_session(token)
    if not session:
        return {"ok": False, "error": "Link ungültig oder abgelaufen"}
    if session.get("already_signed"):
        return {"ok": False, "error": "Vertrag wurde bereits unterschrieben"}
    if not accept:
        return {"ok": False, "error": "Bitte bestätigen Sie die Vertragsbedingungen"}
    if not signer_name.strip():
        return {"ok": False, "error": "Bitte Name eingeben"}
    if not signature_data_url.startswith("data:image"):
        return {"ok": False, "error": "Bitte unterschreiben Sie im Feld"}

    from business_model.contract_send import generate_contract_html

    ref = session["ref"]
    ctype = session["contract_type"]
    data = session.get("contract_data") or {}
    html, _, calc = generate_contract_html(data, {
        "ref": ref,
        "name": signer_name,
        "company": session.get("lead_company"),
        "email": session.get("lead_email"),
        "role_type": "bauherr" if ctype == "bauherr" else "partner",
    })
    signed_html = _embed_signature(
        html,
        name=signer_name.strip(),
        ort=ort.strip() or "—",
        datum=datum.strip() or datetime.now(TZ).strftime("%d.%m.%Y"),
        sig_b64=signature_data_url,
    )

    SIGNED_DIR.mkdir(parents=True, exist_ok=True)
    fname = f"signed-{ctype}-{ref}-{datetime.now(TZ).strftime('%Y%m%d-%H%M')}.html"
    out_path = SIGNED_DIR / fname
    out_path.write_text(signed_html, encoding="utf-8")

    path = TOKENS_DIR / f"{token}.json"
    session["signed"] = True
    session["signed_at"] = _now_iso()
    session["signer_name"] = signer_name
    session["signed_file"] = str(out_path)
    session["signed_html"] = signed_html
    path.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")

    _notify_admin_signed(session, signed_html, fname, signer_name, ort, datum, token=token)
    _crm_mark_signed(ref)

    result = {"ok": True, "ref": ref, "file": fname}
    if token:
        result["signed_document_url"] = signed_document_url(token)
    if ctype == "partner":
        try:
            from matching.intro_retry import try_intro_after_contract
            admin = os.getenv("ADMIN_EMAIL", "").strip()
            intro = try_intro_after_contract(ref, admin)
            if intro:
                result["intro_auto"] = intro
        except Exception as exc:
            result["intro_auto"] = {"ok": False, "error": str(exc)}
    return result


def _crm_mark_signed(ref: str) -> None:
    secret = os.getenv("ADMIN_CRM_SECRET", "").strip()
    url = os.getenv("SHEETS_WEBHOOK_URL", "").strip()
    if not secret or not url:
        return
    try:
        from sheet_client import crm_update
        crm_update(ref, {
            "vertrag": "Ja",
            "stage": "Vertrag unterschrieben",
            "naechster_schritt": "Nächste Schritte einleiten / Intro vorbereiten",
        })
    except Exception:
        pass


def _notify_admin_signed(session: dict, html: str, fname: str, name: str, ort: str, datum: str, *, token: str = "") -> None:
    if not email_configured() or not ADMIN_EMAIL:
        return
    ref = session.get("ref", "")
    token = token or session.get("token", "")
    ctype = "Partner" if session.get("contract_type") == "partner" else "Bauherr"
    doc_url = signed_document_url(token) if token else ""
    subject = f"Kunde hat signiert — {name} ({ref})"
    link_line = f"\nUnterschriebenes Dokument online:\n{doc_url}\n" if doc_url else ""
    text = f"""Kunde hat signiert

Referenz: {ref}
Typ: {ctype}
Unterzeichner: {name}
Ort/Datum: {ort}, {datum}
E-Mail: {session.get('lead_email','')}
{link_line}
Der unterschriebene Vertrag ist im Anhang ({fname}) — dort ist er immer verfügbar.
{('Online-Link: ' + doc_url) if doc_url else ''}
CRM: „Vertrag unterschrieben“

{company_footer_text()}
"""
    link_html = ""
    if doc_url:
        link_html = f"""<p style="margin:20px 0;text-align:center">
<a href="{doc_url}" style="display:inline-block;background:#0b3d2e;color:#fff;text-decoration:none;padding:14px 24px;font-weight:600">Unterschriebenes Dokument online öffnen</a>
</p>
<p style="font-size:13px;color:#666;text-align:center;margin:0 0 16px">
Falls der Link nicht öffnet: unterschriebener Vertrag ist <strong>immer im Anhang</strong> ({fname}).
</p>"""
    else:
        link_html = f"""<p style="font-size:14px;color:#333;margin:16px 0">
<strong>Unterschriebener Vertrag:</strong> siehe Anhang <em>{fname}</em>
</p>"""
    html_body = f"""<div style="font-family:Arial,sans-serif;font-size:15px;line-height:1.6;color:#333">
<p style="font-size:18px;color:#0b3d2e"><strong>Kunde hat signiert</strong></p>
<p><strong>{name}</strong> · {ref} · {ctype}<br>{ort}, {datum}<br>{session.get('lead_email','')}</p>
{link_html}
<p style="font-size:13px;color:#666">CRM wurde aktualisiert. Anhang: {fname}</p>
</div>"""
    att = {
        "filename": fname,
        "content": base64.b64encode(html.encode("utf-8")).decode("ascii"),
    }
    send_email(
        ADMIN_EMAIL,
        subject,
        text,
        html_body,
        reply_to=REPLY_EMAIL,
        attachments=[att],
        mail_kind="transactional",
        entity_ref=ref,
    )
