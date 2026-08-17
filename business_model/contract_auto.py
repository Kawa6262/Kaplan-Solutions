"""Automatischer Vertragsversand nach Website-Anfrage + Retry-Warteschlange."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from company_config import company_footer_text
from lead_followup.config import REPLY_EMAIL
from mailer import ADMIN_EMAIL, email_configured, send_email
from sheet_client import crm_update

TZ = ZoneInfo("Europe/Berlin")
ROOT = Path(__file__).resolve().parent.parent
SENT_PATH = ROOT / "data" / "contract_auto_sent.json"
QUEUE_PATH = ROOT / "data" / "contract_auto_queue.json"
LOG_PATH = ROOT / "data" / "contract_auto.log"


def _enabled() -> bool:
    return os.getenv("AUTO_SEND_CONTRACT", "1").strip().lower() not in ("0", "false", "no", "off")


def _log(msg: str) -> None:
    line = f"{datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(f"[contract-auto] {msg}", flush=True)
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def _load_json(path: Path) -> list | dict:
    if not path.is_file():
        return [] if path.name.endswith("queue.json") else {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return [] if path.name.endswith("queue.json") else {}


def _save_json(path: Path, data: list | dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _already_sent(ref: str) -> bool:
    ref = (ref or "").strip()
    if not ref:
        return False
    sent = _load_json(SENT_PATH)
    if isinstance(sent, dict):
        return ref in sent
    return ref in sent


def _mark_sent(ref: str, meta: dict | None = None) -> None:
    sent = _load_json(SENT_PATH)
    if not isinstance(sent, dict):
        sent = {}
    sent[ref] = {
        "at": datetime.now(TZ).isoformat(timespec="seconds"),
        **(meta or {}),
    }
    _save_json(SENT_PATH, sent)


def _parse_location(loc: str) -> tuple[str, str]:
    loc = (loc or "").strip()
    if not loc or loc in ("—", "-"):
        return "", ""
    m = re.match(r"^(\d{5})\s+(.+)$", loc)
    if m:
        return m.group(2).strip(), m.group(1)
    return loc, ""


def _compose_anschrift(source: dict) -> str:
    parts: list[str] = []
    seen: set[str] = set()
    for key in ("anschrift", "standort", "location", "region", "stadt", "plz"):
        val = str(source.get(key) or "").strip()
        if not val or val in ("—", "-") or val.lower() in seen:
            continue
        seen.add(val.lower())
        parts.append(val)
    return ", ".join(parts)


def inquiry_to_lead(payload: dict) -> dict:
    """Website-Anfrage → Lead-Daten für Vertrags-PDF."""
    role = (payload.get("role") or "").strip()
    is_bau = role == "bauherr"
    name = (payload.get("name") or "").strip()
    company = (payload.get("company_name") or payload.get("company") or "").strip()
    if company in ("—", "-", ""):
        company = name
    if not is_bau and (payload.get("company_name") or "").strip() not in ("", "—", "-"):
        company = (payload.get("company_name") or "").strip()

    loc = (payload.get("location") if is_bau else payload.get("region")) or ""
    stadt = (payload.get("stadt") or "").strip()
    plz = ""
    if not stadt and loc:
        stadt, plz = _parse_location(loc)

    from business_model.contract_send import parse_netto_eur

    netto_raw = ""
    if is_bau:
        netto_raw = payload.get("budget") or ""
    else:
        netto_raw = payload.get("order_scope") or payload.get("budget") or ""

    return {
        "ref": (payload.get("ref") or "").strip(),
        "name": name,
        "company": company,
        "firma": company,
        "email": (payload.get("email") or "").strip(),
        "telefon": (payload.get("phone") or payload.get("telefon") or "").strip(),
        "stadt": stadt,
        "plz": plz,
        "standort": loc.strip() if isinstance(loc, str) else "",
        "anschrift": _compose_anschrift(payload),
        "vertretung": name,
        "role_type": "bauherr" if is_bau else "partner",
        "budget": payload.get("budget") or "",
        "netto": netto_raw,
        "projekt": (payload.get("project") if is_bau else payload.get("trades")) or "",
    }


def inquiry_to_contract_data(payload: dict, lead: dict) -> dict:
    from business_model.contract_send import parse_netto_eur

    is_partner = lead.get("role_type") == "partner"
    netto = parse_netto_eur(lead.get("netto") or lead.get("budget") or 0) if is_partner else 0
    proj = lead.get("projekt") or ""
    return {
        "ref": lead.get("ref"),
        "type": lead.get("role_type"),
        "name": lead.get("name"),
        "firma": lead.get("firma") or lead.get("company"),
        "email": lead.get("email"),
        "telefon": lead.get("telefon"),
        "anschrift": lead.get("anschrift"),
        "vertretung": lead.get("vertretung") or lead.get("name"),
        "netto_eur": netto if netto > 0 else None,
        "region": lead.get("stadt") or "",
        "project_name": proj,
        "mark_sent": True,
    }


def _crm_after_send(ref: str, calc: dict | None) -> None:
    fields: dict = {
        "stage": "Vertrag versendet",
        "naechster_schritt": "Vertrag nachfassen / Unterschrift einholen",
    }
    if calc:
        fields["netto"] = calc.get("netto_order_fmt", "")
        fields["provision"] = calc.get("provision_net_fmt", "")
    try:
        crm_update(ref, fields)
    except Exception as exc:
        _log(f"CRM-Update fehlgeschlagen {ref}: {exc}")


def _notify_admin_sent(payload: dict, result: dict) -> None:
    if not email_configured() or not ADMIN_EMAIL:
        return
    name = payload.get("name") or result.get("to") or "Lead"
    ref = payload.get("ref") or result.get("ref") or "—"
    subject = f"Vertrag automatisch gesendet — {name} ({ref})"
    text = f"""Vertrag automatisch nach Website-Anfrage gesendet

Lead: {name}
E-Mail: {result.get('to', payload.get('email', ''))}
Referenz: {ref}
Vertrag: {result.get('filename', '')}

Der Kunde erhält den Vertrag im Anhang und sendet ihn unterschrieben zurück.

{company_footer_text()}
"""
    html = f"""<div style="font-family:Georgia,serif;font-size:15px;line-height:1.6;color:#222">
<p><strong>Vertrag automatisch gesendet</strong></p>
<p>{name}<br>{result.get('to', '')}<br>Ref. {ref}</p>
<p style="color:#666;font-size:14px">Anhang in Kundenmail: {result.get('filename', '')}</p>
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
    except Exception as exc:
        _log(f"Admin-Hinweis fehlgeschlagen: {exc}")


def _enqueue(payload: dict, error: str) -> None:
    queue = _load_json(QUEUE_PATH)
    if not isinstance(queue, list):
        queue = []
    ref = (payload.get("ref") or "").strip()
    if any(q.get("ref") == ref for q in queue):
        return
    queue.append({
        "ref": ref,
        "payload": payload,
        "error": error[:500],
        "queued_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "attempts": 0,
    })
    _save_json(QUEUE_PATH, queue[-50:])
    _log(f"In Warteschlange: {ref} ({error[:120]})")


def _next_contract_send_time() -> datetime:
    """Standard: nächster Werktag 8:00 Uhr (Berlin). Sofort mit AUTO_CONTRACT_IMMEDIATE=1."""
    if os.getenv("AUTO_CONTRACT_IMMEDIATE", "").strip().lower() in ("1", "true", "yes"):
        return datetime.now(TZ)
    hour = int(os.getenv("AUTO_CONTRACT_SEND_HOUR", "8"))
    now = datetime.now(TZ)
    target = (now + timedelta(days=1)).replace(hour=hour, minute=0, second=0, microsecond=0)
    while target.weekday() >= 5:
        target += timedelta(days=1)
    return target


def auto_send_contract_after_inquiry(payload: dict) -> dict:
    """Nach Bestätigungs-Mail: Vertrag planen (Standard: nächster Tag 8 Uhr) oder sofort."""
    if not _enabled():
        return {"ok": False, "skipped": "AUTO_SEND_CONTRACT aus"}

    ref = (payload.get("ref") or "").strip()
    email = (payload.get("email") or "").strip()
    if not email or "@" not in email:
        return {"ok": False, "skipped": "keine E-Mail"}
    if not ref:
        return {"ok": False, "skipped": "keine Referenz"}

    if _already_sent(ref):
        return {"ok": True, "skipped": "already_sent", "ref": ref}

    if not email_configured():
        _enqueue(payload, "E-Mail nicht konfiguriert")
        return {"ok": False, "error": "E-Mail nicht konfiguriert", "queued": True}

    from business_model.contract_send import schedule_contract_to_lead, send_contract_to_lead

    lead = inquiry_to_lead(payload)
    data = inquiry_to_contract_data(payload, lead)
    send_at = _next_contract_send_time()
    immediate = send_at <= datetime.now(TZ) + timedelta(seconds=30)

    try:
        if immediate:
            result = send_contract_to_lead(data, lead)
        else:
            result = schedule_contract_to_lead(data, lead, scheduled_for=send_at)
    except Exception as exc:
        _enqueue(payload, str(exc))
        return {"ok": False, "error": str(exc), "queued": True}

    if not result.get("ok"):
        _enqueue(payload, result.get("error", "Versand fehlgeschlagen"))
        return {**result, "queued": True}

    if result.get("scheduled"):
        _mark_sent(ref, {"to": result.get("to"), "scheduled_for": result.get("scheduled_for")})
        when = send_at.strftime("%d.%m.%Y %H:%M")
        _log(f"✓ Vertrag geplant → {result.get('to')} ({ref}) · {when} Uhr")
        return {"ok": True, "ref": ref, "scheduled": True, **result}

    _mark_sent(ref, {"to": result.get("to"), "subject": result.get("subject")})
    calc = result.get("provision")
    _crm_after_send(ref, calc)
    _notify_admin_sent(payload, {**result, "ref": ref})
    _log(f"✓ Vertrag gesendet → {result.get('to')} ({ref})")
    return {"ok": True, "ref": ref, **result}


def process_contract_auto_queue(max_items: int = 10) -> int:
    """Fehlgeschlagene Auto-Versände erneut versuchen."""
    if not _enabled() or not email_configured():
        return 0
    queue = _load_json(QUEUE_PATH)
    if not isinstance(queue, list) or not queue:
        return 0

    from business_model.contract_send import send_contract_to_lead

    remaining: list[dict] = []
    sent = 0
    for item in queue[:max_items]:
        payload = item.get("payload") or {}
        ref = (item.get("ref") or payload.get("ref") or "").strip()
        if not ref or _already_sent(ref):
            continue
        lead = inquiry_to_lead(payload)
        data = inquiry_to_contract_data(payload, lead)
        try:
            result = send_contract_to_lead(data, lead)
        except Exception as exc:
            item["attempts"] = int(item.get("attempts") or 0) + 1
            item["last_error"] = str(exc)[:500]
            remaining.append(item)
            continue
        if not result.get("ok"):
            item["attempts"] = int(item.get("attempts") or 0) + 1
            item["last_error"] = result.get("error", "")
            remaining.append(item)
            continue
        _mark_sent(ref, {"to": result.get("to"), "retry": True})
        _crm_after_send(ref, result.get("provision"))
        _notify_admin_sent(payload, {**result, "ref": ref})
        _log(f"✓ Retry OK → {result.get('to')} ({ref})")
        sent += 1

    remaining.extend(queue[max_items:])
    _save_json(QUEUE_PATH, remaining)
    return sent


def run_contract_inbox_jobs() -> dict:
    """Posteingang prüfen + Auto-Queue + geplante Verträge."""
    from business_model import contract_inbox

    scheduled_done = 0
    try:
        from business_model.contract_send import finalize_due_scheduled_contracts

        scheduled_done = finalize_due_scheduled_contracts()
    except Exception as exc:
        _log(f"Geplante Verträge: {exc}")

    inbox = 0
    if contract_inbox.configured():
        try:
            inbox = contract_inbox.check_contract_returns()
        except Exception as exc:
            _log(f"Postfach-Fehler: {exc}")
    else:
        _log("IMAP nicht konfiguriert — Vertrags-Rücksendungen manuell prüfen")

    missed = scan_inbox_for_missed_contracts()
    retry = process_contract_auto_queue()
    return {
        "ok": True,
        "contract_returns": inbox,
        "inbox_resend": missed,
        "auto_retries": retry,
        "scheduled_finalized": scheduled_done,
    }


def scan_inbox_for_missed_contracts(limit_days: int = 7) -> int:
    """Falls Auto-Versand bei Anfrage fehlschlug: aus data/inbox nachholen."""
    inbox_dir = ROOT / "data" / "inbox"
    if not inbox_dir.is_dir():
        return 0
    cutoff = datetime.now(TZ).timestamp() - limit_days * 86400
    sent = 0
    for path in sorted(inbox_dir.glob("*.json")):
        try:
            if path.stat().st_mtime < cutoff:
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                continue
            ref = (payload.get("ref") or "").strip()
            if not ref or _already_sent(ref):
                continue
            result = auto_send_contract_after_inquiry(payload)
            if result.get("ok") and not result.get("skipped"):
                sent += 1
        except Exception as exc:
            _log(f"Inbox-Scan {path.name}: {exc}")
    return sent
