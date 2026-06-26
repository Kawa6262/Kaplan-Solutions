#!/usr/bin/env python3
"""Businessmodell-Briefing per E-Mail — sofort oder geplant (Mitternacht Berlin)."""

from __future__ import annotations

import argparse
import base64
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from business_model.content import build_business_model_html, build_business_model_text
from business_model.contract_document import render_partner_contract_html
from mailer import email_configured, send_email, send_resend

RECIPIENT = "Kawa.f.Kaplan@gmail.com"
SUBJECT = "Kaplan Solutions — Businessmodell, Mustervertrag & Optimierungen (27.06.2026)"


def _roadmap_text() -> str:
    return """
KAPLAN SOLUTIONS — OPTIMIERUNGS-ROADMAP
Stand: 27.06.2026

PHASE 0 — Umsatz freischalten (Woche 1–2)
  [ ] Partner-Vertrag vor Erstkontakt (Gate)
  [ ] Sheet-Spalten: Vertrag, Intro, Netto-Summe, Provision, Rechnung, Bezahlt
  [ ] Anwaltliche Vertragsprüfung
  [ ] kontakt@ Strato → Gmail

PHASE 1 — Erste Rechnungen (Woche 3–6)
  [ ] Rechnungsgenerator (5% netto, min/max)
  [ ] Auto-Versand bei Pipeline „Vermittelt"
  [ ] Mahnung Tag 15 / 28

PHASE 2 — Skalierung (Monat 2–3)
  [ ] Outreach Cloud (Render Cron)
  [ ] Hot-Match Intro-Draft
  [ ] Seriosität-Gate in Matching
  [ ] 3-Touch Outreach + Lead-Nurture

PHASE 3 — Profitabilität (Monat 4–6)
  [ ] Lexoffice/CSV Export
  [ ] KPI-Dashboard
  [ ] Städte-Expansion nach Berlin-Portfolio
"""


def _attachments() -> list[dict]:
    contract_html = render_partner_contract_html()
    text_doc = build_business_model_text()
    roadmap = _roadmap_text()
    return [
        {
            "filename": "Kaplan-Solutions-Vermittlungsvertrag-Partner.html",
            "content": base64.b64encode(contract_html.encode("utf-8")).decode("ascii"),
        },
        {
            "filename": "Kaplan-Solutions-Businessmodell.txt",
            "content": base64.b64encode(text_doc.encode("utf-8")).decode("ascii"),
        },
        {
            "filename": "Kaplan-Solutions-Roadmap.txt",
            "content": base64.b64encode(roadmap.encode("utf-8")).decode("ascii"),
        },
    ]


def _intro_html() -> str:
    return """
<p style="font-size:15px;line-height:1.75;color:#444;margin:0 0 20px">
Hallo Ferhat,<br><br>
hier ist deine <strong>vollständige Ausarbeitung</strong> — Ergebnis von Marktrecherche,
Codebase-Audit und Optimierung an Vertrag, Matching und Automatisierung.
</p>
<p style="font-size:14px;line-height:1.7;color:#555;margin:0 0 16px">
<strong>Heute optimiert:</strong><br>
• Mustervertrag: Abwerbeschutz, Meldepauschale, Pflicht-Anlage, Bauhauptvertrag-Definition<br>
• Google Sheet: Top-Matches Status bleibt bei Rescan erhalten<br>
• Partner-Follow-up: Vermittlungsvertrag vor erstem Intro<br>
• Businessmodell: Marktvergleich, Umsatzplanung, 7-Tage-Plan
</p>
<p style="font-size:14px;color:#666;margin:0 0 24px">
<strong>Anhänge:</strong> Mustervertrag (HTML → PDF) · Businessmodell (TXT) · Roadmap (TXT)
</p>
"""


def build_email_bodies() -> tuple[str, str]:
    inner = build_business_model_html()
    # Nur Inhaltsteil extrahieren und Intro voranstellen
    start = inner.find("<tr><td style=\"padding:32px")
    end = inner.rfind("</td></tr>\n<tr><td style=\"padding:20px")
    if start != -1 and end != -1:
        content = inner[start:end]
        content = content.replace(
            "<tr><td style=\"padding:32px 40px 40px\">",
            f"<tr><td style=\"padding:32px 40px 40px\">{_intro_html()}",
            1,
        )
        html = inner[:start] + content + inner[end:]
    else:
        html = inner

    text = (
        "Hallo Ferhat,\n\n"
        "Anbei dein vollständiges Businessmodell, der optimierte Mustervertrag und die Roadmap.\n\n"
        + build_business_model_text()
    )
    return text, html


def send_now() -> str | None:
    text, html = build_email_bodies()
    return send_resend(
        RECIPIENT,
        SUBJECT,
        text,
        html,
        reply_to=None,
        attachments=_attachments(),
        tags=[{"name": "type", "value": "business-model-briefing"}],
    )


def schedule_midnight() -> str | None:
    text, html = build_email_bodies()
    berlin = ZoneInfo("Europe/Berlin")
    now = datetime.now(berlin)
    target = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if now >= target:
        target = target.replace(day=target.day + 1)
    scheduled_at = target.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")
    return send_resend(
        RECIPIENT,
        SUBJECT,
        text,
        html,
        reply_to=None,
        attachments=_attachments(),
        scheduled_at=scheduled_at,
        tags=[{"name": "type", "value": "business-model-briefing"}],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Businessmodell-Briefing senden")
    parser.add_argument(
        "--now",
        action="store_true",
        help="Sofort senden statt Mitternacht",
    )
    args = parser.parse_args()

    if not email_configured():
        print("E-Mail nicht konfiguriert (RESEND_API_KEY / ADMIN_EMAIL).", file=sys.stderr)
        return 1

    try:
        if args.now:
            email_id = send_now()
            print(f"Gesendet. Resend-ID: {email_id}")
        else:
            berlin = ZoneInfo("Europe/Berlin")
            now = datetime.now(berlin)
            target = now.replace(hour=0, minute=0, second=0, microsecond=0)
            if now >= target:
                from datetime import timedelta
                target = target + timedelta(days=1)
            email_id = schedule_midnight()
            print(f"Geplant für {target.strftime('%d.%m.%Y %H:%M')} Berlin. Resend-ID: {email_id}")
    except Exception as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
