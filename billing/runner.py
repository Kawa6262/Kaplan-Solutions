"""Rechnungsgenerator — scannt CRM, versendet Provision-Rechnungen."""

from __future__ import annotations

import base64
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from billing.invoice_template import build_invoice
from billing.provision import calculate_provision, _parse_eur
from file_util import read_json, write_json_atomic
from mailer import email_configured, send_email

_STORE = Path(__file__).resolve().parent.parent / "data" / "invoices_sent.json"
_COUNTER = Path(__file__).resolve().parent.parent / "data" / "invoice_counter.json"

INVOICE_STAGES = {
    "Auftrag über Vermittlung",
    "Provision fällig",
    "Auftrag ueber Vermittlung",
}


def _load_sent() -> dict:
    try:
        data = read_json(_STORE)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_sent(data: dict) -> None:
    write_json_atomic(_STORE, data)


def _next_invoice_no() -> str:
    year = datetime.now(ZoneInfo("Europe/Berlin")).year
    try:
        data = read_json(_COUNTER)
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}
    key = str(year)
    n = int(data.get(key, 0)) + 1
    data[key] = n
    write_json_atomic(_COUNTER, data)
    return f"RE-{year}-{n:04d}"


def _lead_needs_invoice(lead: dict) -> bool:
    if lead.get("role_type") != "partner":
        return False
    if str(lead.get("vertrag") or "").strip().lower() != "ja":
        return False
    if str(lead.get("rechnung") or "").strip().lower() in ("ja", "gesendet", "1"):
        return False
    if str(lead.get("bezahlt") or "").strip().lower() == "ja":
        return False
    netto = _parse_eur(str(lead.get("netto") or ""))
    if netto <= 0:
        return False
    stage = str(lead.get("stage") or "")
    if stage not in INVOICE_STAGES and not os.getenv("BILLING_FORCE_ANY_STAGE", "").strip():
        return False
    return True


def generate_and_send_invoice(lead: dict, *, force: bool = False) -> dict:
    ref = str(lead.get("ref") or "").strip()
    if not ref:
        return {"ok": False, "error": "ref fehlt"}
    sent = _load_sent()
    if not force and ref in sent:
        return {"ok": True, "skipped": "already_invoiced", "ref": ref}
    if not email_configured():
        return {"ok": False, "error": "E-Mail nicht konfiguriert"}

    email = str(lead.get("email") or "").strip()
    if not email:
        return {"ok": False, "error": "partner email fehlt"}

    netto = _parse_eur(str(lead.get("netto") or ""))
    amounts = calculate_provision(netto)
    invoice_no = _next_invoice_no()
    project = f"{lead.get('stadt', '')} · {lead.get('branche', '')}".strip(" ·")
    subject, text, html = build_invoice(
        invoice_no=invoice_no,
        partner_name=str(lead.get("name") or ""),
        partner_company=str(lead.get("firma") or lead.get("name") or ""),
        partner_email=email,
        ref=ref,
        project_desc=project or "Vermitteltes Bauvorhaben",
        amounts=amounts,
    )
    attachment = {
        "filename": f"{invoice_no}.html",
        "content": base64.b64encode(html.encode("utf-8")).decode("ascii"),
    }
    admin = os.getenv("ADMIN_EMAIL", "").strip()
    send_email(email, subject, text, html, attachments=[attachment])
    if admin and admin.lower() != email.lower():
        send_email(
            admin,
            f"[Kopie] {subject}",
            text,
            html,
            attachments=[attachment],
        )

    try:
        from sheet_client import crm_update

        crm_update(ref, {
            "provision": amounts["provision_net_fmt"],
            "rechnung": "Ja",
            "stage": "Provision fällig",
        })
    except Exception as exc:
        print(f"[billing] CRM-Update: {exc}", flush=True)

    sent[ref] = {
        "invoice_no": invoice_no,
        "sent_at": datetime.now(ZoneInfo("Europe/Berlin")).isoformat(timespec="seconds"),
        "gross": amounts["gross_total"],
    }
    _save_sent(sent)
    print(f"[billing] ✓ Rechnung {invoice_no} → {email} ({amounts['gross_total_fmt']} €)", flush=True)
    return {
        "ok": True,
        "ref": ref,
        "invoice_no": invoice_no,
        "email": email,
        "gross": amounts["gross_total_fmt"],
    }


def process_due_invoices(force: bool = False) -> dict:
    from sheet_client import crm_snapshot

    snap = crm_snapshot()
    if not snap.get("ok"):
        return {"ok": False, "error": snap.get("error", "snapshot fehlgeschlagen")}
    leads = snap.get("leads") or []
    results = []
    for lead in leads:
        if not force and not _lead_needs_invoice(lead):
            continue
        if force:
            netto = _parse_eur(str(lead.get("netto") or ""))
            if netto <= 0 or lead.get("role_type") != "partner":
                continue
        results.append(generate_and_send_invoice(lead, force=force))
    sent = sum(1 for r in results if r.get("ok") and not r.get("skipped"))
    return {"ok": True, "scanned": len(leads), "processed": len(results), "sent": sent, "results": results}
