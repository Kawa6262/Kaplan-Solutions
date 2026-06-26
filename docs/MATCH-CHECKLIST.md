# Match-Checkliste — Kaplan Solutions

Wenn ein **heißer Match (≥ 75 %)** entsteht, passiert automatisch:

1. **Du** bekommst eine E-Mail mit allen Infos + dieser Checkliste
2. **Der Bauherr** bekommt eine E-Mail: „Passender Partner gefunden — wir melden uns für einen Termin"
3. **Drive-Ordner** wird unter `Kaplan Leads/03_Matches/` angelegt

---

## Deine Checkliste (nur du)

| # | Aufgabe | Wer |
|---|---------|-----|
| 1 | Partner-Vertrag unterschrieben? | Du — **vor** dem Intro |
| 2 | Match-Ordner in Drive prüfen | System (automatisch) |
| 3 | Intro-Mail vorbereiten (CC Bauherr + Partner) | Du |
| 4 | Anlage „Vermittelter Kontakt" ausfüllen | Du |
| 5 | **Termin fürs Erstgespräch** | **Du — das Einzige was du wirklich machen musst** |
| 6 | Sheet: Status → „In Kontakt" | Du (1 Klick) |
| 7 | Nach Vertragsschluss: Rechnung stellen | System (bald automatisch) |

---

## Was das System für dich macht

- Lead erfassen, prüfen, matchen
- Sofort-Mail an dich + Bauherr bei heißem Match
- Match-Ordner mit Checkliste in Drive
- Tägliches Briefing 10:00
- Follow-ups, Outreach, Reports

---

## Einrichtung (einmalig)

1. **Google Apps Script** neu deployen (Code mit Sofort-Alerts)
2. Im Sheet Tab `_Meta` → Zelle **B6** (`match_alert_secret`): denselben Wert wie `CRON_SECRET` auf Render eintragen
3. Auf Render: `MATCH_ALERT_SECRET` = gleicher Wert (oder `CRON_SECRET` wird mitverwendet)
