"""Businessmodell-Inhalt — Kaplan Solutions Vermittlung Bau (vollständig)."""

from __future__ import annotations

from company_config import COMPANY
from provisions_config import PROVISIONS

BRAND = COMPANY.get("brand", "Kaplan Solutions")
OPERATOR = COMPANY.get("operator_name") or "Ferhat Kaplan"
STREET = COMPANY.get("street", "Hochstraße 8")
ZIP_CITY = COMPANY.get("zip_city", "13357 Berlin")
EMAIL = COMPANY.get("email", "kontakt@kaplan-solutions.de")
PHONE = COMPANY.get("phone", "+49 159 01309199")
SITE = COMPANY.get("website", "https://kaplan-solutions.de")

PARTNER_PCT = PROVISIONS["partner_percent"]
PARTNER_MIN = PROVISIONS["partner_min"]
PARTNER_MAX = PROVISIONS["partner_max"]
FOLLOWUP_MONTHS = PROVISIONS["partner_followup_months"]


def build_business_model_text() -> str:
    return f"""
══════════════════════════════════════════════════════════════════════════════
KAPLAN SOLUTIONS — STRATEGISCHES BUSINESSMODELL
Stand: 27. Juni 2026 · Ausarbeitung für Ferhat Kaplan
══════════════════════════════════════════════════════════════════════════════

TEIL A — EXECUTIVE SUMMARY
──────────────────────────────────────────────────────────────────────────────
Kaplan Solutions ist eine B2B-Vermittlungsplattform im Bauwesen (§§ 652, 652a BGB).
Du verbindest Bauherren/Investoren mit geprüften Bauunternehmen — persönlich betreut,
technisch automatisiert.

Kernentscheidung (final):
  • Bauherr zahlt: 0 % (kostenfrei = maximale Nachfrage)
  • Partner zahlt: {PARTNER_PCT} % netto bei Erfolg (min. {PARTNER_MIN} €, max. {PARTNER_MAX} €)
  • Keine Doppelbelastung beider Seiten (Standard)

Marktvergleich:
  • Handwerkerportale: oft 30–150 €/Monat + 10–40 € pro Kontakt ODER 5–15 % Provision
  • Klassische Auftragsvermittler (Handwerk): bis 13 % (HWS Hamburg, Branchenbericht)
  • Kaplan Solutions: 5 % netto, kein Abo, kein Risiko vor Auftrag — unter Markt, seriös

══════════════════════════════════════════════════════════════════════════════
TEIL B — GESCHÄFTSMODELL IM DETAIL
══════════════════════════════════════════════════════════════════════════════

1. WERTVERSprechen (Warum jemand bei dir mitmacht)
──────────────────────────────────────────────────
Bauherren / Investoren:
  ✓ Kostenfreie Erstberatung und Vermittlung
  ✓ Vorauswahl: Region, Gewerk, Budget, Seriositätsprüfung
  ✓ Persönlicher Ansprechpartner (du) — kein anonymes Portal
  ✓ Diskrete Abwicklung, professionelle Kommunikation

Partner-Unternehmen (Auftragnehmer):
  ✓ Qualifizierte Projektanfragen statt teurer Kaltakquise
  ✓ Keine Listengebühr, keine monatliche Grundgebühr
  ✓ Zahlen nur bei Erfolg (Hauptvertrag unterschrieben)
  ✓ Klare Vertragsgrundlage + Nachweis-Anlage pro Intro
  ✓ Cap bei {PARTNER_MAX} € macht Großprojekte attraktiv

Kaplan Solutions (dein Vorteil):
  ✓ Skalierbares Erfolgshonorar ohne Lager/Produktion/Personal-Overhead
  ✓ Automatisierung senkt Grenzkosten pro Lead (24/7 System)
  ✓ Netzwerkeffekt: mehr Bauherren → mehr Partner → mehr Umsatz
  ✓ Hohe Marge bei erfolgreicher Vermittlung (Ø 7.500 €/Deal)

2. PREISMODELL & BEISPIELRECHNUNGEN
──────────────────────────────────────────────────
Standard-Konditionen Partner:
  • {PARTNER_PCT} % der Netto-Auftragssumme (ohne USt.)
  • Minimum: {PARTNER_MIN} € je Hauptvertrag
  • Maximum: {PARTNER_MAX} € je Hauptvertrag (Cap)
  • Fällig: 14 Tage nach Vertragsschluss / erster Anzahlung / Baubeginn
  • Nachvertraglich: {FOLLOWUP_MONTHS} Monate (gleicher Bauherr = Provision)
  • Keine Aufnahmegebühr (Standard)

  Auftrag (netto)     Provision ({PARTNER_PCT} %)
  ─────────────────   ──────────────────────────
   30.000 €            1.500 € (Minimum greift)
   50.000 €            2.500 €
  100.000 €            5.000 €
  150.000 €            7.500 €  ← realistischer Durchschnitt
  300.000 €           15.000 €
  500.000 €           25.000 €
  700.000 €           35.000 € (Cap greift)
 2.000.000 €           35.000 € (Cap — effektiv 1,75 %)

Optional (Premium, später):
  • Exklusiv-Mandat Bauherr: Beratungspauschale 500–2.000 €
  • Großprojekt-Betreuung: individuell schriftlich

3. WETTBEWERBSVERGLEICH
──────────────────────────────────────────────────
                    │ MyHammer/Portale │ Klass. Vermittler │ Kaplan Solutions
  ──────────────────┼──────────────────┼───────────────────┼─────────────────
  Bauherr-Kosten    │ 0 €              │ 0 €               │ 0 € ✓
  Partner-Kosten    │ Abo + pro Kontakt│ 10–13 %           │ 5 % netto ✓
  Vorabkosten       │ Ja (Abo/Kontakt) │ Nein              │ Nein ✓
  Qualifizierung    │ Gering           │ Mittel            │ Hoch (Matching+Seriosität)
  Persönliche Betr. │ Nein             │ Ja                │ Ja ✓
  Automatisierung   │ Portal           │ Manuell           │ 24/7 System ✓

Dein Vorteil: Du bist günstiger als klassische Vermittler, qualifizierter als reine
Portale, und persönlicher als beides.

══════════════════════════════════════════════════════════════════════════════
TEIL C — KUNDENREISE (Lead → Zahlung)
══════════════════════════════════════════════════════════════════════════════

Phase 1 — LEAD (Tag 0)
  Kanäle: Website-Formular, Telefon, Outreach-Antwort
  System: Google Sheet, Drive-Ordner, Seriositätsprüfung, Bestätigungsmail
  Deine Rolle: —

Phase 2 — QUALIFIZIERUNG (Tag 0–2)
  System: Follow-up 08:00 Folgetag, stündlicher Match-Scan
  Du: Daten prüfen, Partner-Vertrag unterschreiben lassen (PFLICHT vor Intro!)
  Gate: Kein Erstkontakt ohne unterschriebenen Rahmenvertrag

Phase 3 — MATCHING & ERSTKONTAKT (Tag 2–7)
  System: Top Matches Tab, Briefing 10:00, Match ≥75 % = „Jetzt anrufen"
  Du: Erstgespräch koordinieren (CC beide Parteien), Anlage „Vermittelter Kontakt" senden
  KPI: Hot Match innerhalb 48h bearbeiten

Phase 4 — VERHANDLUNG (Woche 2–8)
  Partner ↔ Bauherr schließen Bauhauptvertrag
  Partner meldet Abschluss (Vertragspflicht § 4 — 7 Werktage)
  System (geplant): Reminder bei fehlendem Status-Update

Phase 5 — PROVISION
  Berechnung: clamp(Netto × {PARTNER_PCT} %, {PARTNER_MIN}, {PARTNER_MAX}) + USt.
  Rechnung an Partner, 14 Tage Zahlungsziel
  System (geplant): Auto-Rechnung + Mahnung Tag 15/28

Phase 6 — ABSCHLUSS
  Pipeline-Status „Vermittelt", Buchhaltungsexport
  Optional: Zufriedenheits-Follow-up beide Seiten

══════════════════════════════════════════════════════════════════════════════
TEIL D — AUTOMATISIERUNG (IST-ZUSTAND & ROADMAP)
══════════════════════════════════════════════════════════════════════════════

BEREITS AKTIV (24/7):
  ✓ Lead-Erfassung Website → Google Sheet + Drive
  ✓ Seriositätsprüfung (Handelsregister, Google, Rechtsform)
  ✓ Lead-Follow-up 08:00 + Abschluss-Fazit an Admin
  ✓ Outreach ~40 Firmen/Tag (Warm-up, Spam-optimiert)
  ✓ Matching stündlich + Briefing 10:00
  ✓ Outreach-Tagesbericht 18:00
  ✓ Top-Matches Status bleibt bei Rescan erhalten (neu optimiert)

OPTIMIERT HEUTE ABEND:
  ✓ Mustervertrag Partner: Abwerbeschutz, Meldepauschale, Bauhauptvertrag-Definition
  ✓ Anlage „Vermittelter Kontakt" ist Pflicht bei jedem Intro
  ✓ Businessmodell vollständig ausgearbeitet (dieses Dokument)

ROADMAP — PHASE 0 (Woche 1–2, Umsatz freischalten):
  ○ Sheet-Spalten: Vertrag (Ja/Nein), Intro gesendet, Netto-Summe, Provision, Rechnung, Bezahlt
  ○ Partner-Follow-up: Link zum Vermittlungsvertrag
  ○ Anwaltliche Vertragsprüfung vor erster bezahlter Vermittlung (~500–1.500 €)

ROADMAP — PHASE 1 (Woche 3–6, erste Rechnungen):
  ○ Rechnungsgenerator: Provision auto-berechnen + PDF
  ○ Auto-Versand bei Pipeline-Status „Vermittelt"
  ○ Mahnung Tag 15 / 28

ROADMAP — PHASE 2 (Monat 2–3, Skalierung):
  ○ Outreach in Cloud (Render Cron, Mac-unabhängig)
  ○ Hot-Match Intro-Draft automatisch
  ○ Seriosität <40 % aus Top Matches filtern
  ○ 3-Touch Outreach + Lead-Nurture Sequenz

ROADMAP — PHASE 3 (Monat 4–6, Profitabilität):
  ○ Lexoffice/CSV Buchhaltungsexport
  ○ KPI-Dashboard (Funnel: Outreach → Form → Match → Vertrag → €)
  ○ kontakt@ Postfach Strato → Gmail

══════════════════════════════════════════════════════════════════════════════
TEIL E — UMSATZPLANUNG JAHR 1
══════════════════════════════════════════════════════════════════════════════

Konservativ (1 Vermittlung/Monat, Ø 80.000 € netto):
  → 4.000 €/Monat × 12 = 48.000 €/Jahr (vor Steuern & Kosten)

Realistisch (2–3 Vermittlungen/Monat, Ø 150.000 € netto):
  → 7.500 € × 2,5 = 18.750 €/Monat ≈ 225.000 €/Jahr

Optimistisch (4 Vermittlungen/Monat + 1 Großprojekt/Quartal):
  → ~270.000–350.000 €/Jahr

Kritischer Pfad zum Umsatz (nicht Lead-Volumen!):
  1. Partner-Vertrag unterschrieben
  2. Hot Match ≥75 % innerhalb 48h bearbeitet
  3. Intro mit Anlage dokumentiert
  4. Hauptvertrag → Rechnung → Zahlung

Fixkosten (geschätzt):
  • Resend, Render, Google: ~50–100 €/Monat
  • Domain/Strato: ~15 €/Monat
  • Anwalt (einmalig): ~500–1.500 €
  → Break-even: 1 Vermittlung alle 2 Monate (konservativ)

══════════════════════════════════════════════════════════════════════════════
TEIL F — DEINE ROLLE vs. SYSTEM
══════════════════════════════════════════════════════════════════════════════

DU (high value, 2–4h/Tag):
  • Matching-Briefing 10:00 — heiße Matches anrufen
  • Partner-Verträge unterschreiben lassen
  • Erstgespräche koordinieren (CC-Mail)
  • Große Projekte persönlich begleiten
  • Beziehungspflege Top-Partner

SYSTEM (24/7, automatisch):
  • Leads sammeln, prüfen, matchen
  • Follow-ups, Outreach, Reports
  • Dokumentation Sheet/Drive
  • Rechnungen & Mahnungen (ab Phase 1)

Täglicher Rhythmus:
  08:00  Lead-Follow-ups raus
  09:00  Outreach startet (40/Tag)
  10:00  Matching-Briefing → DU handelst
  18:00  Outreach-Report

══════════════════════════════════════════════════════════════════════════════
TEIL G — RECHTLICHER RAHMEN
══════════════════════════════════════════════════════════════════════════════

  • Vermittlung: §§ 652, 652a BGB (Nachweis vs. Vermittlung — Standard: §652a)
  • B2B-Outreach: § 7 Abs. 3 UWG (branchenübliche Kontaktaufnahme)
  • AGB + Vermittlungsvertrag Partner (Anhang dieser Mail)
  • Anlage bei jedem Intro = Beweissicherung
  • Anwaltliche Prüfung vor Ersteinsatz empfohlen (einmalig)

══════════════════════════════════════════════════════════════════════════════
TEIL H — NÄCHSTE 7 TAGE (KONKRET)
══════════════════════════════════════════════════════════════════════════════

Tag 1: Mustervertrag aus Anhang ausdrucken/unterschreiben (eigene Vorlage)
Tag 2: kontakt@ Weiterleitung Strato → Gmail einrichten
Tag 3: Ersten Partner aus Sheet kontaktieren → Vertrag unterschreiben lassen
Tag 4: Bei Hot Match ≥75 %: Intro-Mail mit Anlage senden
Tag 5: Pipeline-Spalten im Sheet erweitern (Vertrag, Rechnung, Bezahlt)
Tag 6: Anwalt-Termin für Vertragsprüfung vereinbaren
Tag 7: Erste Vermittlung aktiv anstoßen

══════════════════════════════════════════════════════════════════════════════
{BRAND}
{OPERATOR}
{STREET}, {ZIP_CITY}
{EMAIL} · {PHONE}
{SITE}
══════════════════════════════════════════════════════════════════════════════
"""


def build_business_model_html() -> str:
    gold = "#b87333"
    green = "#0b3d2e"
    html_sections = f"""
<p style="font-size:13px;color:#888;margin:0 0 24px;border-bottom:1px solid #eee;padding-bottom:16px">
<strong>Ausarbeitung für Ferhat Kaplan</strong> · Stand 27.06.2026 ·
Basierend auf Marktrecherche, Codebase-Audit und Optimierung aller Systeme
</p>

<h2 style="color:{green};font-family:Georgia,serif;margin-top:0">Executive Summary</h2>
<p style="font-size:15px;line-height:1.75;color:#333">
<strong>Kaplan Solutions</strong> vermittelt Bauherren an geprüfte Bauunternehmen —
für Bauherren <strong>kostenfrei</strong>, für Partner <strong>{PARTNER_PCT}&nbsp;% netto nur bei Erfolg</strong>
(min. {PARTNER_MIN}&nbsp;€ · max. {PARTNER_MAX}&nbsp;€). Unter klassischen Vermittlern (10–13&nbsp;%),
ohne Abo-Gebühren wie Portale.
</p>

<h2 style="color:{green};font-family:Georgia,serif">1. Wer bezahlt — und warum?</h2>
<table style="width:100%;border-collapse:collapse;margin:16px 0;font-size:14px">
<tr style="background:{green};color:#d9b75a">
  <th style="padding:10px;text-align:left">Partei</th>
  <th style="padding:10px;text-align:left">Provision</th>
  <th style="padding:10px;text-align:left">Begründung</th>
</tr>
<tr><td style="padding:10px;border-bottom:1px solid #eee"><strong>Bauherr</strong></td>
    <td style="padding:10px;border-bottom:1px solid #eee;color:#15803d"><strong>0&nbsp;%</strong></td>
    <td style="padding:10px;border-bottom:1px solid #eee">Maximale Nachfrage — wie MyHammer, Check24</td></tr>
<tr style="background:#fafafa"><td style="padding:10px;border-bottom:1px solid #eee"><strong>Partner</strong></td>
    <td style="padding:10px;border-bottom:1px solid #eee"><strong>{PARTNER_PCT}&nbsp;% netto</strong><br>
    <small>min. {PARTNER_MIN}&nbsp;€ · max. {PARTNER_MAX}&nbsp;€</small></td>
    <td style="padding:10px;border-bottom:1px solid #eee">Bekommt Umsatz — zahlt für qualifizierten Lead</td></tr>
</table>

<h2 style="color:{green};font-family:Georgia,serif">2. Marktvergleich</h2>
<table style="width:100%;border-collapse:collapse;font-size:13px;margin:12px 0">
<tr style="background:#f7f7f7"><th style="padding:8px;text-align:left"></th>
<th style="padding:8px">Portale</th><th style="padding:8px">Klass. Vermittler</th>
<th style="padding:8px;background:#f0fdf4">Kaplan Solutions</th></tr>
<tr><td style="padding:8px;border-bottom:1px solid #eee">Bauherr</td>
<td style="padding:8px;border-bottom:1px solid #eee">0 €</td>
<td style="padding:8px;border-bottom:1px solid #eee">0 €</td>
<td style="padding:8px;border-bottom:1px solid #eee;background:#f0fdf4"><strong>0 € ✓</strong></td></tr>
<tr><td style="padding:8px;border-bottom:1px solid #eee">Partner</td>
<td style="padding:8px;border-bottom:1px solid #eee">Abo + Kontakt</td>
<td style="padding:8px;border-bottom:1px solid #eee">10–13 %</td>
<td style="padding:8px;border-bottom:1px solid #eee;background:#f0fdf4"><strong>{PARTNER_PCT} % ✓</strong></td></tr>
<tr><td style="padding:8px">Vorabkosten</td>
<td style="padding:8px">Ja</td><td style="padding:8px">Nein</td>
<td style="padding:8px;background:#f0fdf4"><strong>Nein ✓</strong></td></tr>
</table>

<h2 style="color:{green};font-family:Georgia,serif">3. Beispiel-Rechnungen</h2>
<table style="width:100%;border-collapse:collapse;font-size:14px">
<tr style="background:#f7f7f7"><th style="padding:8px;text-align:left">Auftrag (netto)</th><th style="padding:8px">Provision</th></tr>
<tr><td style="padding:8px;border-bottom:1px solid #eee">50.000&nbsp;€</td><td style="padding:8px;border-bottom:1px solid #eee"><strong>2.500&nbsp;€</strong></td></tr>
<tr><td style="padding:8px;border-bottom:1px solid #eee">150.000&nbsp;€</td><td style="padding:8px;border-bottom:1px solid #eee"><strong>7.500&nbsp;€</strong> ← Ø realistisch</td></tr>
<tr><td style="padding:8px;border-bottom:1px solid #eee">500.000&nbsp;€</td><td style="padding:8px;border-bottom:1px solid #eee"><strong>25.000&nbsp;€</strong></td></tr>
<tr><td style="padding:8px">2.000.000&nbsp;€</td><td style="padding:8px"><strong>35.000&nbsp;€</strong> (Cap — effektiv 1,75&nbsp;%)</td></tr>
</table>

<h2 style="color:{green};font-family:Georgia,serif">4. Kundenreise bis zur Zahlung</h2>
<ol style="line-height:2;color:#444;font-size:14px">
<li><strong>Lead</strong> — Website / Outreach → Sheet + Drive <span style="color:#15803d">(automatisch)</span></li>
<li><strong>Qualifizierung</strong> — Seriosität, Match, <strong>Partner-Vertrag unterschrieben</strong> <span style="color:{gold}">(du)</span></li>
<li><strong>Erstkontakt</strong> — Briefing 10 Uhr, Intro mit Anlage <span style="color:{gold}">(du, innerhalb 48h)</span></li>
<li><strong>Verhandlung</strong> — Partner ↔ Bauherr Hauptvertrag</li>
<li><strong>Provision</strong> — Rechnung {PARTNER_PCT}&nbsp;%, 14 Tage Zahlungsziel</li>
<li><strong>Abschluss</strong> — Pipeline „Vermittelt", Buchhaltung</li>
</ol>

<h2 style="color:{green};font-family:Georgia,serif">5. Automatisierung — heute optimiert</h2>
<p style="color:#444;line-height:1.7"><strong style="color:#15803d">Aktiv 24/7:</strong> Leads, Follow-ups 8 Uhr, Outreach 40/Tag, Matching stündlich, Briefing 10 Uhr, Report 18 Uhr.</p>
<p style="color:#444;line-height:1.7"><strong style="color:#15803d">Heute verbessert:</strong> Top-Matches Status bleibt erhalten · Mustervertrag rechtlich verschärft (Abwerbeschutz, Meldepauschale, Pflicht-Anlage).</p>
<p style="color:#444;line-height:1.7"><strong style="color:{gold}">Als Nächstes:</strong> Rechnungsmodul · Partner-Vertrags-Gate · Hot-Match Intro-Automation · kontakt@ Postfach.</p>

<h2 style="color:{green};font-family:Georgia,serif">6. Umsatzpotenzial Jahr 1</h2>
<table style="width:100%;border-collapse:collapse;font-size:14px">
<tr style="background:#f7f7f7"><th style="padding:8px;text-align:left">Szenario</th><th style="padding:8px">Annahme</th><th style="padding:8px">Jahresumsatz</th></tr>
<tr><td style="padding:8px;border-bottom:1px solid #eee">Konservativ</td>
<td style="padding:8px;border-bottom:1px solid #eee">1×/Monat à 80k €</td>
<td style="padding:8px;border-bottom:1px solid #eee"><strong>~48.000&nbsp;€</strong></td></tr>
<tr><td style="padding:8px;border-bottom:1px solid #eee">Realistisch</td>
<td style="padding:8px;border-bottom:1px solid #eee">2–3×/Monat à 150k €</td>
<td style="padding:8px;border-bottom:1px solid #eee"><strong>~225.000&nbsp;€</strong></td></tr>
<tr><td style="padding:8px">Optimistisch</td>
<td style="padding:8px">4×/Monat + Großprojekte</td>
<td style="padding:8px"><strong>~350.000&nbsp;€</strong></td></tr>
</table>
<p style="font-size:13px;color:#666;margin-top:8px">
Kritischer Pfad: Nicht Lead-Volumen, sondern <strong>unterschriebener Partner-Vertrag → Hot Match in 48h → Rechnung</strong>.
</p>

<h2 style="color:{green};font-family:Georgia,serif">7. Dein Tagesrhythmus</h2>
<table style="width:100%;font-size:14px;border-collapse:collapse">
<tr style="background:#f7f7f7"><th style="padding:8px">Zeit</th><th style="padding:8px">Was passiert</th><th style="padding:8px">Wer</th></tr>
<tr><td style="padding:8px;border-bottom:1px solid #eee">08:00</td>
<td style="padding:8px;border-bottom:1px solid #eee">Lead-Follow-ups</td>
<td style="padding:8px;border-bottom:1px solid #eee">System</td></tr>
<tr><td style="padding:8px;border-bottom:1px solid #eee">09–18</td>
<td style="padding:8px;border-bottom:1px solid #eee">Outreach ~40 Firmen</td>
<td style="padding:8px;border-bottom:1px solid #eee">System</td></tr>
<tr><td style="padding:8px;border-bottom:1px solid #eee"><strong>10:00</strong></td>
<td style="padding:8px;border-bottom:1px solid #eee"><strong>Matching-Briefing → anrufen!</strong></td>
<td style="padding:8px;border-bottom:1px solid #eee"><strong>Du</strong></td></tr>
<tr><td style="padding:8px">18:00</td>
<td style="padding:8px">Outreach-Report</td>
<td style="padding:8px">System</td></tr>
</table>

<h2 style="color:{green};font-family:Georgia,serif">8. Nächste 7 Tage</h2>
<ol style="line-height:1.9;color:#444;font-size:14px">
<li>Mustervertrag (Anhang) bei Partner unterschreiben lassen</li>
<li>kontakt@ Weiterleitung Strato → Gmail</li>
<li>Ersten Partner aus Sheet kontaktieren</li>
<li>Bei Hot Match ≥75&nbsp;%: Intro mit Anlage senden</li>
<li>Pipeline-Spalten erweitern (Vertrag, Rechnung, Bezahlt)</li>
<li>Anwalt-Termin für Vertragsprüfung</li>
<li>Erste Vermittlung aktiv anstoßen</li>
</ol>

<h2 style="color:{green};font-family:Georgia,serif">9. Mustervertrag (Anhang)</h2>
<p style="color:#444;line-height:1.7">
Im Anhang: <strong>Vermittlungsvertrag Partner-Unternehmen</strong> — heute Abend optimiert mit:
Abwerbeschutz · Meldepauschale · Bauhauptvertrag-Definition · Pflicht-Anlage bei jedem Intro.<br>
Online: <a href="{SITE}/vermittlungsvertrag/partner" style="color:{gold}">{SITE}/vermittlungsvertrag/partner</a>
</p>

<p style="margin-top:32px;padding:16px;background:#faf6f0;border-left:3px solid {gold};color:#555;font-size:13px;line-height:1.6">
<strong>Rechtlicher Hinweis:</strong> Mustervertrag vor Ersteinsatz von einem Fachanwalt für Handelsrecht prüfen lassen (einmalig ~500–1.500&nbsp;€). Individuelle Konditionen bei Großprojekten schriftlich vereinbaren.
</p>
"""
    return f"""<!DOCTYPE html><html lang="de"><head><meta charset="utf-8"></head>
<body style="margin:0;background:#f0f0f0;font-family:Arial,Helvetica,sans-serif">
<table width="100%" cellspacing="0" cellpadding="0" style="background:#f0f0f0;padding:32px 16px">
<tr><td align="center">
<table width="640" style="max-width:640px;background:#fff;border:1px solid #e0e0e0">
<tr><td style="padding:36px 40px 24px;background:{green};border-bottom:3px solid {gold}">
  <p style="margin:0 0 6px;font-size:10px;letter-spacing:0.35em;color:{gold};text-transform:uppercase">Kaplan Solutions</p>
  <h1 style="margin:0;font-family:Georgia,serif;font-size:26px;color:#fff;font-weight:400">Strategisches Businessmodell</h1>
  <p style="margin:10px 0 0;color:#c8d4ce;font-size:14px">Vollständige Ausarbeitung · 27.06.2026 · Mit Mustervertrag</p>
</td></tr>
<tr><td style="padding:32px 40px 40px">{html_sections}</td></tr>
<tr><td style="padding:20px 40px;background:#fafafa;border-top:1px solid #eee;font-size:12px;color:#888">
  {OPERATOR} · {STREET}, {ZIP_CITY}<br>{EMAIL} · {PHONE}<br>{SITE}
</td></tr>
</table></td></tr></table></body></html>"""
