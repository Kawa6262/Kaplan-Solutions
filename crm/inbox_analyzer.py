"""Eingehende Mails analysieren, Kawa informieren, Aktionen auslösen."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Berlin")

_INTENTS = {
    "bauherr_anfrage": "Auftraggeber / Bauvorhaben",
    "partner_interesse": "Partner / Auftragnehmer",
    "unterlagen_anfrage": "Unterlagen / Vertrag angefordert",
    "rueckfrage": "Rückfrage / Klärung",
    "allgemein": "Allgemeine Anfrage",
}


def _rule_intent(subject: str, body: str) -> tuple[str, str]:
    text = f"{subject}\n{body}".lower()
    if re.search(r"(vertrag|unterlagen|dokument|pdf|angebot|offerte)", text):
        return "unterlagen_anfrage", "Fragt nach Vertrag, Unterlagen oder Dokumenten."
    if re.search(
        r"(bauherr|auftraggeber|bauvorhaben|sucht.*(auftragnehmer|partner|firma)|"
        r"generalunternehmer|gu[\s-]?|neubau|sanierung.*projekt)",
        text,
    ):
        return "bauherr_anfrage", "Möglicher Auftraggeber mit Bauvorhaben oder Partnerbedarf."
    if re.search(r"(partnerschaft|aufträge|auftraege|subunternehmer|gewerk)", text):
        return "partner_interesse", "Partner / Auftragnehmer zeigt Interesse."
    if re.search(r"(rückfrage|rueckfrage|frage|bitte.*(schicken|senden|melden))", text):
        return "rueckfrage", "Allgemeine Rückfrage — bitte persönlich prüfen."
    return "allgemein", "Allgemeine Kontaktanfrage."


def _ai_analyze(subject: str, body: str, from_email: str, from_name: str) -> dict | None:
    try:
        from crm import copilot_ai

        if not copilot_ai.configured():
            return None
    except Exception:
        return None

    prompt = f"""Analysiere diese eingehende B2B-Mail für Kaplan Solutions (Bauvermittlung).
Antworte NUR als JSON:
{{"intent":"bauherr_anfrage|partner_interesse|unterlagen_anfrage|rueckfrage|allgemein",
"summary":"2-3 Sätze Deutsch, was der Absender will",
"priority":"hoch|normal|niedrig",
"suggested_action":"konkrete Empfehlung für Ferhat/Kawa",
"create_lead":true/false,
"role":"bauherr|partner|unbekannt"}}

Von: {from_name} <{from_email}>
Betreff: {subject}
Text:
{body[:3500]}"""

    try:
        return copilot_ai.complete_json(
            system="Du bist CRM-Analyst. Nur gültiges JSON, keine Markdown-Fences.",
            user=prompt,
            max_tokens=500,
        )
    except Exception:
        return None


def analyze(subject: str, body: str, *, from_email: str = "", from_name: str = "") -> dict:
    intent, rule_summary = _rule_intent(subject, body)
    out = {
        "intent": intent,
        "intent_label": _INTENTS.get(intent, intent),
        "summary": rule_summary,
        "priority": "normal",
        "suggested_action": "Im CRM Posteingang prüfen und antworten.",
        "create_lead": intent in ("bauherr_anfrage", "partner_interesse"),
        "role": "bauherr" if intent == "bauherr_anfrage" else "partner" if intent == "partner_interesse" else "unbekannt",
    }
    ai = _ai_analyze(subject, body, from_email, from_name)
    if ai:
        out["intent"] = ai.get("intent") or out["intent"]
        out["intent_label"] = _INTENTS.get(out["intent"], out["intent"])
        out["summary"] = (ai.get("summary") or out["summary"]).strip()
        out["priority"] = ai.get("priority") or out["priority"]
        out["suggested_action"] = (ai.get("suggested_action") or out["suggested_action"]).strip()
        out["create_lead"] = bool(ai.get("create_lead", out["create_lead"]))
        out["role"] = ai.get("role") or out["role"]
    return out


def _forward_to_gmail(*, from_email: str, from_name: str, subject: str, body: str, analysis: dict) -> None:
    if os.getenv("INBOX_FORWARD_GMAIL", "1").strip().lower() in ("0", "false", "no"):
        return
    admin = os.getenv("ADMIN_EMAIL", "").strip()
    if not admin:
        return
    try:
        from mailer import email_configured, send_email

        if not email_configured():
            return
        subj = f"[Kaplan Posteingang] {subject or 'Neue Mail'}"
        text = (
            f"Neue Mail an kontakt@kaplan-solutions.de\n\n"
            f"Von: {from_name} <{from_email}>\n"
            f"Betreff: {subject}\n\n"
            f"--- Analyse ---\n"
            f"Art: {analysis.get('intent_label')}\n"
            f"{analysis.get('summary')}\n\n"
            f"Empfehlung: {analysis.get('suggested_action')}\n\n"
            f"--- Original ---\n"
            f"{body[:4000]}"
        )
        send_email(admin, subj, text, f"<pre style='white-space:pre-wrap'>{text}</pre>", mail_kind="transactional")
    except Exception:
        pass


def _notify_assistant(from_email: str, from_name: str, subject: str, analysis: dict, actions: list[str]) -> None:
    try:
        from crm import copilot

        who = from_name or from_email or "Unbekannt"
        lines = [
            f"Hey Kawa — neue Mail von {who}",
            f"Betreff: {subject or '—'}",
            "",
            analysis.get("summary", ""),
            "",
            f"→ {analysis.get('suggested_action')}",
        ]
        if actions:
            lines.extend(["", "Erledigt:"] + [f"• {a}" for a in actions])
        copilot.add_message(role="assistant", text="\n".join(lines))
    except Exception:
        pass


def _create_portfolio_lead(
    *, from_email: str, from_name: str, subject: str, body: str, analysis: dict
) -> str | None:
    if not analysis.get("create_lead"):
        return None
    role = analysis.get("role") or "unbekannt"
    is_bau = role == "bauherr"
    payload = {
        "role": "bauherr" if is_bau else "unternehmen",
        "name": from_name or from_email.split("@")[0],
        "email": from_email,
        "company_name": from_name or "",
        "message": f"E-Mail: {subject}\n\n{body[:2000]}",
        "lead_source": "E-Mail Posteingang",
        "timestamp": datetime.now(TZ).isoformat(timespec="seconds"),
    }
    if is_bau:
        payload["project"] = subject or "Anfrage per E-Mail"
    else:
        payload["trades"] = analysis.get("intent_label", "Partner")
    try:
        from server import forward_to_sheet

        meta = forward_to_sheet(payload)
        return meta.get("ref")
    except Exception:
        return None


def _update_crm_stage(from_email: str, analysis: dict) -> str | None:
    try:
        from sheet_client import crm_snapshot, crm_update

        email_l = from_email.lower()
        for lead in crm_snapshot().get("leads") or []:
            if (lead.get("email") or "").lower() == email_l:
                stage = "Erstgespräch geplant"
                if analysis.get("intent") == "unterlagen_anfrage":
                    stage = "Vertrag versendet"
                crm_update(lead["ref"], {"stage": stage, "notiz": analysis.get("summary", "")[:500]})
                return lead["ref"]
    except Exception:
        pass
    return None


def process_inbound(
    *,
    message_id: str,
    from_email: str,
    from_name: str,
    subject: str,
    body: str,
    notify: bool = True,
) -> dict:
    analysis = analyze(subject, body, from_email=from_email, from_name=from_name)
    actions: list[str] = []

    ref = _update_crm_stage(from_email, analysis)
    if ref:
        actions.append(f"CRM aktualisiert ({ref})")

    new_ref = _create_portfolio_lead(
        from_email=from_email,
        from_name=from_name,
        subject=subject,
        body=body,
        analysis=analysis,
    )
    if new_ref:
        actions.append(f"Ins Portfolio aufgenommen ({new_ref})")

    if notify:
        _forward_to_gmail(
            from_email=from_email,
            from_name=from_name,
            subject=subject,
            body=body,
            analysis=analysis,
        )
        actions.append("Kopie an deine Gmail geschickt")
        _notify_assistant(from_email, from_name, subject, analysis, actions)

    try:
        from crm.mail_inbox import save_analysis

        save_analysis(message_id, analysis)
    except Exception:
        pass

    return {"ok": True, "analysis": analysis, "actions": actions}
