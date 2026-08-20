"""Regelbasierter Kaplan-Sales-Assistent — ohne KI-API, 0 €."""

from __future__ import annotations

import json
import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
TZ = ZoneInfo("Europe/Berlin")

REF_RE = re.compile(r"\b(KS-20\d{2}-[A-Z0-9-]+)\b", re.IGNORECASE)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")
STAGE_ALIASES: dict[str, str] = {
    "neu": "Neu",
    "lead": "Lead",
    "kontaktiert": "Kontaktiert",
    "erstgespräch": "Erstgespräch geplant",
    "erstgespraech": "Erstgespräch geplant",
    "qualifiziert": "Qualifiziert",
    "vertrag": "Vertrag versendet",
    "vertrag versendet": "Vertrag versendet",
    "vertrag gesendet": "Vertrag versendet",
    "vertrag unterschrieben": "Vertrag unterschrieben",
    "unterschrieben": "Vertrag unterschrieben",
    "portfolio": "Im Portfolio",
    "im portfolio": "Im Portfolio",
    "match": "Match erhalten",
    "provision": "Provision fällig",
    "aktiv": "Aktiver Partner",
    "verloren": "Verloren / Inaktiv",
    "pause": "Verloren / Pause",
    "auftrag": "Auftrag erteilt",
    "abgeschlossen": "Abgeschlossen",
}


def ai_enabled() -> bool:
    return os.getenv("COPILOT_AI", "0").strip().lower() in ("1", "true", "yes")


def handle(user_text: str) -> str:
    text = (user_text or "").strip()
    if not text:
        return "Bitte eine Frage oder einen Befehl schreiben."

    snap = _snapshot()

    for fn in (
        _cmd_send_mail,
        _cmd_update_stage,
        _cmd_test_mail,
        _cmd_help,
        _cmd_greeting,
        _cmd_status,
        _cmd_outreach,
        _cmd_projekt,
        _cmd_inbox,
        _cmd_hot_leads,
        _cmd_crm_stats,
        _cmd_termine,
        _cmd_tasks,
        _cmd_opportunities,
        _cmd_matches,
        _cmd_lead_by_ref,
        _cmd_lead_search,
        _cmd_freeform,
    ):
        reply = fn(text, snap)
        if reply:
            return reply

    return _unknown(text, snap)


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def _snapshot() -> dict:
    try:
        from sheet_client import crm_snapshot

        return crm_snapshot() or {}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _leads(snap: dict) -> list[dict]:
    return list(snap.get("leads") or [])


def _format_lead(l: dict, *, detail: bool = False) -> str:
    lines = [
        f"📋 {l.get('ref')} — {l.get('name') or l.get('company') or '—'}",
        f"Firma: {l.get('company') or '—'}",
        f"Stage: {l.get('stage') or '—'} · Status: {l.get('lead_status') or '—'}",
        f"E-Mail: {l.get('email') or '—'} · Tel: {l.get('telefon') or '—'}",
        f"Ort: {l.get('stadt') or '—'} · Projekt: {l.get('project') or '—'}",
    ]
    if detail:
        if l.get("best_match"):
            lines.append(f"Best Match: {l.get('best_match')}")
        if l.get("naechster_schritt"):
            lines.append(f"Nächster Schritt: {l.get('naechster_schritt')}")
        if l.get("naechster_termin"):
            lines.append(f"Termin: {l.get('naechster_termin')}")
        if l.get("notizen"):
            lines.append(f"Notiz: {(l.get('notizen') or '')[:200]}")
        if l.get("quelle"):
            lines.append(f"Quelle: {l.get('quelle')}")
    return "\n".join(lines)


def _search_leads(query: str, snap: dict, *, limit: int = 8) -> list[dict]:
    q = _norm(query)
    if not q:
        return []
    leads = _leads(snap)
    scored: list[tuple[int, dict]] = []
    tokens = [t for t in re.split(r"\W+", q) if len(t) >= 2]
    for l in leads:
        blob = _norm(
            " ".join(
                str(l.get(k) or "")
                for k in (
                    "ref",
                    "name",
                    "company",
                    "email",
                    "stadt",
                    "project",
                    "stage",
                    "lead_status",
                    "telefon",
                    "notizen",
                )
            )
        )
        score = 0
        if q in blob:
            score += 10
        for t in tokens:
            if t in blob:
                score += 3
        ref = (l.get("ref") or "").lower()
        if ref and ref in q:
            score += 20
        if score:
            scored.append((score, l))
    scored.sort(key=lambda x: (-x[0], x[1].get("ref") or ""))
    return [l for _, l in scored[:limit]]


def _resolve_stage(name: str, snap: dict) -> str | None:
    raw = _norm(name).strip()
    if raw in STAGE_ALIASES:
        return STAGE_ALIASES[raw]
    all_stages = list(snap.get("partner_stages") or []) + list(snap.get("bauherr_stages") or [])
    for st in all_stages:
        if _norm(st) == raw or raw in _norm(st):
            return st
    for key, val in STAGE_ALIASES.items():
        if key in raw or raw in key:
            return val
    return None


def _outreach_lines() -> list[str]:
    lines: list[str] = []
    try:
        from outreach import config, storage

        storage.init_db()
        s = storage.stats_summary()
        if s.get("total", 0) > 0 or s.get("today_projekt_sent", 0):
            lines.append(
                f"• Partner: {s.get('today_sent', 0)}/{config.DAILY_SEND_LIMIT} heute, "
                f"{s.get('queued', 0)} Warteschlange"
            )
            if config.PROJEKT_ENABLED:
                lines.append(
                    f"• Duisburg ({config.CAMPAIGN_PROJEKT}): "
                    f"{s.get('today_projekt_sent', 0)}/{config.PROJEKT_DAILY_SEND_LIMIT} heute, "
                    f"{s.get('projekt_queued', 0)} wartend, "
                    f"{s.get('projekt_sent_all_time', 0)} gesamt"
                )
            try:
                from outreach import reliability

                lines.append(f"• Fenster: {reliability.window_status_line()}")
            except Exception:
                pass
            return lines
    except Exception:
        pass

    live_path = ROOT / "data" / "outreach_live.json"
    if live_path.is_file():
        try:
            live = json.loads(live_path.read_text(encoding="utf-8"))
            camps = live.get("campaigns") or {}
            for key, label in (
                ("projekt", "Duisburg Projekt"),
                ("partner", "Partner"),
                ("referral", "Referral"),
                ("bauherr", "Bauherr"),
            ):
                c = camps.get(key) or {}
                if c:
                    lines.append(
                        f"• {label}: {c.get('sent_today', 0)}/{c.get('daily_limit', '—')} heute, "
                        f"{c.get('queued', 0)} wartend"
                    )
            if live.get("synced_at"):
                lines.append(f"• Stand Mac-Sync: {live.get('synced_at')}")
        except Exception:
            pass
    if not lines:
        lines.append("• Keine lokalen Outreach-Daten (läuft auf dem Mac — Sync via Live-Push)")
    return lines


def _cmd_help(text: str, snap: dict) -> str | None:
    t = _norm(text)
    if t not in (
        "help",
        "hilfe",
        "befehle",
        "commands",
        "?",
        "was kannst du",
        "was kannst du?",
        "menu",
    ) and not re.search(r"\b(hilfe|befehle|was kannst)\b", t):
        return None
    return (
        "Kaplan Sales Assistent (regelbasiert, kostenlos)\n\n"
        "📊 Überblick\n"
        "• status — CRM + Outreach + Posteingang\n"
        "• outreach / duisburg — Mailversand Zahlen\n"
        "• KS-2026-DU-01 — Projekt Duisburg Details\n\n"
        "📥 Posteingang\n"
        "• posteingang / inbox — syncen & anzeigen\n"
        "• sync inbox — nur synchronisieren\n\n"
        "🎯 Leads & Pipeline\n"
        "• hot leads / vertrag — heiße Leads\n"
        "• neue leads — frische Anfragen\n"
        "• termine heute — Termine\n"
        "• aufgaben / tasks — offene Tasks\n"
        "• opportunities — Chancen\n"
        "• matches — Top-Matches\n"
        "• KS-2026-1234 — Lead-Details\n"
        "• Suche: „bki“, „atakor“, Name, Firma, E-Mail\n\n"
        "✉️ E-Mail\n"
        "• test mail / schick testmail\n"
        "• antwort an email@firma.de: Ihr Text\n"
        "• mail an email@firma.de betreff X: Text\n\n"
        "⚙️ Stage ändern\n"
        "• KS-2026-1234 auf vertrag\n"
        "• setze KS-2026-1234 stage vertrag versendet\n\n"
        "Freitext-Fragen funktionieren auch, z. B.:\n"
        "„Wie viele Leads?“ · „Was steht im Posteingang?“ · „Zeig mir BKI“"
    )


def _cmd_greeting(text: str, snap: dict) -> str | None:
    t = _norm(text)
    if re.match(r"^(hi|hallo|hey|moin|servus|guten (morgen|tag|abend)|grüezi|gruesse)\b", t):
        return f"Hallo Kawa 👋\n\n{_cmd_status('status', snap)}"
    return None


def _cmd_status(text: str, snap: dict) -> str | None:
    t = _norm(text)
    if t not in ("status", "stand", "übersicht", "uebersicht", "bericht", "dashboard", "zusammenfassung"):
        if not re.search(r"\b(wie läuft|wie laeuft|überblick|ueberblick|kurzstatus|was ist der stand)\b", t):
            return None
    lines = ["📊 Kaplan Sales — Status", ""]
    st = snap.get("stats") or {}
    if snap.get("ok"):
        lines.append(
            f"• CRM: {st.get('total', 0)} Leads ({st.get('open', 0)} offen), "
            f"{st.get('opportunities', 0)} Opportunities"
        )
        lines.append(
            f"  Bauherr: {st.get('bauherr', 0)} · Partner: {st.get('partner', 0)} · "
            f"Hot Matches: {st.get('hot_matches', 0)}"
        )
        lines.append(
            f"  Heute: {st.get('termine_heute', 0)} Termine, {st.get('tasks_today', 0)} Tasks"
        )
        if snap.get("updated"):
            lines.append(f"  Sheet: {snap.get('updated')}")
    else:
        lines.append(f"• CRM: {snap.get('error', 'Sheet nicht erreichbar')}")
    lines.append("")
    lines.append("📧 Outreach")
    lines.extend(_outreach_lines())
    try:
        from crm.mail_inbox import config_status, list_messages

        cs = config_status()
        if cs.get("configured"):
            m = list_messages(limit=3)
            lines.append("")
            lines.append(f"📥 Posteingang: {m.get('unread', 0)} ungelesen / {m.get('total', 0)} gesamt")
            for msg in m.get("messages") or []:
                subj = (msg.get("subject") or "")[:45]
                lines.append(f"  – {msg.get('from_email')}: {subj}")
        else:
            lines.append("")
            lines.append("📥 Posteingang: nicht konfiguriert")
    except Exception:
        pass
    return "\n".join(lines)


def _cmd_outreach(text: str, snap: dict) -> str | None:
    t = _norm(text)
    if not re.search(r"\b(outreach|mailversand|versendet|newsletter|cold mail)\b", t):
        if not re.search(r"\b(duisburg|projekt).{0,20}(outreach|mail|versand|läuft|laeuft)\b", t):
            if t not in ("duisburg", "outreach", "mailversand"):
                return None
    lines = ["📧 Outreach / Mailversand", ""]
    lines.extend(_outreach_lines())
    try:
        from outreach import config

        if config.PROJEKT_ENABLED and not config.PROJEKT_SEND_ENABLED:
            lines.append("• Hinweis: Projekt-Versand ist in .env gesperrt (OUTREACH_PROJEKT_SEND_ENABLED=0)")
        if config.DAILY_SEND_LIMIT == 0:
            lines.append("• Partner-Outreach pausiert (OUTREACH_DAILY_LIMIT=0) — Fokus Duisburg")
    except Exception:
        pass
    return "\n".join(lines)


def _cmd_projekt(text: str, snap: dict) -> str | None:
    if not re.search(r"\b(KS-2026-DU-01|duisburg|ausschreibung|14 we|mfh)\b", _norm(text), re.I):
        if REF_RE.search(text.upper()) and "DU-01" not in text.upper():
            return None
        if "KS-2026-DU-01" not in text.upper() and "duisburg" not in _norm(text):
            return None
    try:
        from outreach.projekt import AKTUELL

        a = AKTUELL
        lines = [
            f"🏗️ {a.referenz} — {a.titel}",
            f"Region: {a.region}",
            f"Volumen: ca. {a.volumen_gesamt:,} € brutto · {a.einheiten_gesamt} WE".replace(",", "."),
            "",
            "Leistungen (Auszug):",
        ]
        for leist in a.alle_leistungen[:8]:
            lines.append(f"• {leist}")
        lines.append("")
        lines.extend(_outreach_lines())
        return "\n".join(lines)
    except Exception as exc:
        return f"Projekt-Info: {exc}"


def _cmd_inbox(text: str, snap: dict) -> str | None:
    t = _norm(text)
    sync_only = "sync" in t and "post" in t or t in ("sync inbox", "inbox sync", "posteingang sync")
    if not sync_only and not re.search(r"\b(posteingang|inbox|postfach|eingehend|neue mail|neue mails)\b", t):
        if not re.search(r"\b(was steht|zeig.*mail|mail.*posteingang)\b", t):
            return None
    from crm.mail_inbox import list_messages, sync_inbox

    if sync_only:
        r = sync_inbox()
        if not r.get("ok"):
            return f"Sync fehlgeschlagen: {r.get('error')}"
        return f"✓ Posteingang synchronisiert — {r.get('new', 0)} neu, {r.get('total', r.get('processed', '—'))} gesamt"

    r = sync_inbox()
    if not r.get("ok"):
        return f"Posteingang: {r.get('error')}"
    m = list_messages(limit=10)
    if not m.get("messages"):
        return "📥 Posteingang ist leer."
    lines = [f"📥 {m.get('unread', 0)} ungelesen / {m.get('total', 0)} gesamt", ""]
    for msg in m.get("messages") or []:
        lines.append(f"• {msg.get('from_name') or msg.get('from_email')}")
        lines.append(f"  {msg.get('subject') or '(Kein Betreff)'}")
        if msg.get("analysis_summary"):
            lines.append(f"  💡 {msg.get('analysis_intent')}: {msg.get('analysis_summary')}")
        elif msg.get("body"):
            lines.append(f"  {(msg.get('body') or '')[:120]}…")
        if msg.get("crm_ref"):
            lines.append(f"  → Lead {msg.get('crm_ref')}")
    return "\n".join(lines)


def _cmd_hot_leads(text: str, snap: dict) -> str | None:
    t = _norm(text)
    if t not in (
        "hot leads",
        "heisse leads",
        "heiss leads",
        "hot",
        "pipeline",
        "vertrag",
        "verträge",
        "vertraege",
    ) and not re.search(r"\b(hot lead|heiße lead|heisse lead|vertrag lead|vertragslead)\b", t):
        if not (t.startswith("hot") and len(t) < 25):
            return None
    leads = _leads(snap)
    hot = [
        l
        for l in leads
        if "Vertrag" in (l.get("stage") or "")
        or (l.get("priority") or "").lower() in ("hot", "heiss", "🔥")
        or (parse_int(l.get("best_match")) or 0) >= 75
    ]
    if not hot:
        hot = [l for l in leads if not l.get("terminal")][:10]
        title = "📋 Offene Leads (keine Vertrag-Stages gefunden)"
    else:
        title = "🔥 Heiße Leads / Vertrag"
    lines = [title, ""]
    for l in hot[:12]:
        lines.append(
            f"• {l.get('ref')} — {l.get('name') or l.get('company')} "
            f"({l.get('stage')}) {l.get('email') or ''}"
        )
    return "\n".join(lines)


def parse_int(s) -> int | None:
    try:
        return int(str(s).replace("%", "").strip())
    except (TypeError, ValueError):
        return None


def _cmd_crm_stats(text: str, snap: dict) -> str | None:
    t = _norm(text)
    if not re.search(r"\b(wie viele|anzahl|wieviel|how many|statistik|stats)\b", t):
        if t not in ("leads", "lead anzahl", "crm"):
            return None
    if not re.search(r"\b(lead|crm|kontakt|anfrage|opportunity|chance)\b", t) and t not in ("leads", "crm"):
        return None
    st = snap.get("stats") or {}
    lines = ["📈 CRM-Zahlen", ""]
    lines.append(f"• Leads gesamt: {st.get('total', 0)}")
    lines.append(f"• Offen: {st.get('open', 0)} (Inbound: {st.get('open_inbound', 0)}, Cold: {st.get('open_cold', 0)})")
    lines.append(f"• Bauherr: {st.get('bauherr', 0)} · Partner: {st.get('partner', 0)}")
    lines.append(f"• Opportunities: {st.get('opportunities', 0)} ({st.get('open_opportunities', 0)} offen)")
    lines.append(f"• Hot Matches: {st.get('hot_matches', 0)}")
    return "\n".join(lines)


def _cmd_termine(text: str, snap: dict) -> str | None:
    t = _norm(text)
    if not re.search(r"\b(termin|termine|kalender|heute termin)\b", t):
        return None
    items = list(snap.get("termine_heute") or [])
    if not items:
        leads = [l for l in _leads(snap) if l.get("naechster_termin")]
        items = leads[:8]
    if not items:
        return "Heute keine Termine im CRM."
    lines = ["📅 Termine heute", ""]
    for l in items[:10]:
        lines.append(
            f"• {l.get('ref')} — {l.get('name') or l.get('company')} · {l.get('naechster_termin')}"
        )
    return "\n".join(lines)


def _cmd_tasks(text: str, snap: dict) -> str | None:
    t = _norm(text)
    if not re.search(r"\b(aufgabe|aufgaben|task|tasks|todo)\b", t):
        return None
    tasks = list(snap.get("tasks_today") or [])
    if not tasks:
        tasks = [a for a in (snap.get("activities") or []) if a.get("type") == "Task" and a.get("status") != "Completed"][:10]
    if not tasks:
        return "Keine offenen Aufgaben."
    lines = ["✓ Aufgaben", ""]
    for a in tasks[:12]:
        lines.append(f"• [{a.get('status')}] {a.get('subject')} — fällig {a.get('due') or '—'}")
    return "\n".join(lines)


def _cmd_opportunities(text: str, snap: dict) -> str | None:
    t = _norm(text)
    if not re.search(r"\b(opportunity|opportunities|chancen|chance|deals)\b", t):
        return None
    opps = list(snap.get("opportunities") or [])
    open_opps = [o for o in opps if not o.get("terminal")]
    if not open_opps:
        return "Keine offenen Opportunities."
    lines = ["💰 Opportunities", ""]
    for o in open_opps[:12]:
        lines.append(
            f"• {o.get('id')} — {o.get('name')} · {o.get('stage')} · "
            f"{o.get('ag_ref') or ''}{(' / ' + o.get('an_ref')) if o.get('an_ref') else ''}"
        )
    return "\n".join(lines)


def _cmd_matches(text: str, snap: dict) -> str | None:
    t = _norm(text)
    if not re.search(r"\b(match|matches|matching|passung|heiß|heiss)\b", t):
        return None
    hot = list(snap.get("hot_matches") or [])
    if not hot:
        hot = sorted(
            _leads(snap),
            key=lambda l: parse_int(l.get("best_match")) or 0,
            reverse=True,
        )[:8]
    lines = ["🎯 Top Matches", ""]
    for l in hot[:10]:
        lines.append(
            f"• {l.get('ref')} — {l.get('name') or l.get('company')} · Match {l.get('best_match') or '—'}"
        )
    return "\n".join(lines)


def _cmd_lead_by_ref(text: str, snap: dict) -> str | None:
    m = REF_RE.search(text.upper())
    if not m:
        return None
    ref = m.group(1).upper()
    if ref == "KS-2026-DU-01":
        return _cmd_projekt(text, snap)
    for l in _leads(snap):
        if (l.get("ref") or "").upper() == ref:
            return _format_lead(l, detail=True)
    return f"Lead {ref} nicht gefunden."


def _cmd_lead_search(text: str, snap: dict) -> str | None:
    t = _norm(text)
    if re.search(r"\b(status|outreach|posteingang|inbox|hilfe|help|test mail|testmail)\b", t):
        return None
    email = EMAIL_RE.search(text)
    if email:
        hits = _search_leads(email.group(0), snap, limit=5)
        if hits:
            if len(hits) == 1:
                return _format_lead(hits[0], detail=True)
            lines = [f"🔍 Leads zu {email.group(0)}", ""]
            for l in hits:
                lines.append(f"• {l.get('ref')} — {l.get('name') or l.get('company')} ({l.get('stage')})")
            return "\n".join(lines)

    if re.search(r"\b(zeig|zeige|such|suche|finde|find|info|details|wer ist|was ist mit)\b", t):
        q = re.sub(r"\b(zeig|zeige|such|suche|finde|find|info|details|wer ist|was ist mit|mir|den|die|das|bitte)\b", " ", t)
        q = re.sub(r"\s+", " ", q).strip()
        if len(q) >= 2:
            hits = _search_leads(q, snap, limit=6)
            if hits:
                if len(hits) == 1:
                    return _format_lead(hits[0], detail=True)
                lines = [f"🔍 Treffer für „{q.strip()}“", ""]
                for l in hits:
                    lines.append(
                        f"• {l.get('ref')} — {l.get('name') or l.get('company')} "
                        f"({l.get('stage')}) {l.get('email') or ''}"
                    )
                return "\n".join(lines)

    if len(t) >= 3 and len(t) <= 40 and not re.search(r"\b(wie|was|warum|wann|wo)\b", t):
        hits = _search_leads(text, snap, limit=6)
        if hits and (len(hits) == 1 or hits[0].get("ref", "").lower() in t):
            if len(hits) == 1:
                return _format_lead(hits[0], detail=True)
    return None


def _cmd_freeform(text: str, snap: dict) -> str | None:
    t = _norm(text)
    if re.search(r"\b(neue lead|neue anfrage|neue leads|frische lead|heute reingekommen)\b", t):
        leads = _leads(snap)
        today = datetime.now(TZ).strftime("%d.%m.%Y")
        fresh = [l for l in leads if today in (l.get("datum") or l.get("created") or "")]
        if not fresh:
            fresh = sorted(leads, key=lambda x: x.get("ref") or "", reverse=True)[:8]
            lines = ["🆕 Neueste Leads (nach Ref.)", ""]
        else:
            lines = ["🆕 Neue Leads heute", ""]
        for l in fresh[:10]:
            lines.append(f"• {l.get('ref')} — {l.get('name') or l.get('company')} ({l.get('stage')})")
        return "\n".join(lines)

    if re.search(r"\b(wer bin ich|bist du|ki|assistent)\b", t):
        return (
            "Ich bin dein Kaplan Sales Assistent — regelbasiert, ohne API-Kosten.\n"
            "Schreib „hilfe“ für alle Befehle."
        )

    hits = _search_leads(text, snap, limit=3)
    if hits and len(hits) == 1:
        return _format_lead(hits[0], detail=True)
    if hits and len(hits) > 1:
        lines = ["Meinst du einen dieser Leads?", ""]
        for l in hits[:5]:
            lines.append(f"• {l.get('ref')} — {l.get('name') or l.get('company')}")
        lines.append("\nGenauer: KS-2026-XXXX oder „zeig mir …“")
        return "\n".join(lines)
    return None


def _cmd_send_mail(text: str, snap: dict) -> str | None:
    from crm.copilot import _send_test_mail, _wants_test_mail

    if _wants_test_mail(text):
        return _send_test_mail()

    patterns = [
        r"^(?:antwort|reply|mail|email|e-mail)\s+(?:an\s+)?([^\s:@]+@[^\s:@]+)\s*[:]\s*(.+)$",
        r"^(?:schick|sende|send)\s+(?:eine?\s+)?(?:mail|e-mail|email)\s+(?:an\s+)?([^\s:@]+@[^\s:@]+)\s*[:]\s*(.+)$",
        r"^(?:mail|email)\s+(?:an\s+)?([^\s:@]+@[^\s:@]+)\s+betreff\s+(.+?)\s*[:]\s*(.+)$",
    ]
    for pat in patterns:
        m = re.match(pat, text.strip(), re.IGNORECASE | re.DOTALL)
        if m:
            from crm.mail_inbox import send_reply

            groups = m.groups()
            to_addr = groups[0].strip().lower()
            if len(groups) == 3:
                subject, body = groups[1].strip(), groups[2].strip()
            else:
                subject, body = "Kaplan Solutions", groups[1].strip()
            r = send_reply(to_email=to_addr, subject=subject, body=body)
            if r.get("ok"):
                return f"✓ Mail gesendet an {to_addr}"
            return f"Mail fehlgeschlagen: {r.get('error')}"
    return None


def _cmd_test_mail(text: str, snap: dict) -> str | None:
    from crm.copilot import _send_test_mail, _wants_test_mail

    if _wants_test_mail(text):
        return _send_test_mail()
    t = _norm(text)
    if t in ("test mail", "testmail", "test-mail", "test"):
        return _send_test_mail()
    return None


def _cmd_update_stage(text: str, snap: dict) -> str | None:
    m = re.search(
        r"(?:setze|stage|status|auf)\s+(KS-20\d{2}-[A-Z0-9-]+)\s+(?:auf|stage|status)?\s*(.+)$",
        text,
        re.IGNORECASE,
    )
    if not m:
        m = re.search(
            r"(KS-20\d{2}-[A-Z0-9-]+)\s+(?:auf|→|->)\s*(.+)$",
            text,
            re.IGNORECASE,
        )
    if not m:
        return None
    ref = m.group(1).upper()
    stage_raw = m.group(2).strip().rstrip(".")
    stage = _resolve_stage(stage_raw, snap)
    if not stage:
        return f"Stage „{stage_raw}“ nicht erkannt. Beispiel: vertrag, lead, kontaktiert"
    from sheet_client import crm_update

    r = crm_update(ref, {"stage": stage})
    if r.get("ok"):
        return f"✓ {ref} → Stage „{stage}“"
    return f"Update fehlgeschlagen: {r.get('error')}"


def _unknown(text: str, snap: dict) -> str:
    return (
        f"Das habe ich nicht eindeutig verstanden: „{text[:120]}“\n\n"
        "Probiere:\n"
        "• status · posteingang · hot leads · hilfe\n"
        "• KS-2026-XXXX (Lead-Details)\n"
        "• Firmenname oder E-Mail suchen\n"
        "• antwort an email@firma.de: Text\n\n"
        f"{_cmd_status('status', snap)}"
    )
