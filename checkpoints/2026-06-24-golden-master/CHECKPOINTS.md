# Kontrollpunkte — Kaplan Solutions

Gespeicherte Versionen des Projekts, auf die Sie jederzeit zurückspringen können.

## ★ Golden Master (Fundament)

| Name | Datum | Beschreibung |
|------|-------|--------------|
| **`2026-06-24-golden-master`** | 24.06.2026 | **★ GOLDEN MASTER** — Stabile Basis: Lead-System, Matching, Seriosität, FAQ, Rückruf, Spam-Schutz, SEO. Live getestet (KS-2026-0043). Siehe `GOLDEN-MASTER.md` |

**Wiederherstellen (Standard):**
```bash
./restore-checkpoint.sh
```

**Git-Tag:** `golden-master`

---

## Ältere Kontrollpunkte

| Name | Datum | Beschreibung |
|------|-------|--------------|
| `2026-06-02-lead-system-komplett` | 02.06.2026 | Anfrage-Nr., Sheet, Matching (vor Intelligence-Upgrade) |
| `2026-05-31-mails-komplett-verifiziert` | 31.05.2026 | Domain verifiziert (SPF+DKIM+DMARC), Absender kontakt@ |
| `2026-05-29-resend-funktioniert` | 29.05.2026 | Resend live, schöne Lead-Mail |
| `2026-05-26-formular-funktioniert` | 26.05.2026 | FormSubmit, Rollenwahl |
| `2026-05-19-alles-funktioniert` | 19.05.2026 | Formular, Rechtsseiten, Berlin |

## Wiederherstellen (bestimmter Checkpoint)

```bash
./restore-checkpoint.sh 2026-06-24-golden-master
```

Danach Server neu starten (lokal):

```bash
./start.sh
```

## Was gespeichert wird

- Website: `index.html`, `styles.css`, `script.js`, `contact-form.js`
- Backend: `server.py`, `mailer.py`, `trust_score.py`, `wsgi.py`
- Google: `scripts/google-leads-automation.gs`
- SEO: `robots.txt`, `sitemap.xml`, Favicons
- Rechtliches, Config, Deploy-Dateien

## Was nicht gespeichert wird

- `.env` / Render-Secrets — bleiben im Hosting-Dashboard
- `data/inbox/` — eingegangene Anfragen
- Google Sheet/Drive-Inhalte — separat sichern

## Neuen Kontrollpunkt anlegen

```bash
NAME="2026-XX-XX-beschreibung"
mkdir -p "checkpoints/$NAME/scripts"
rsync -a index.html styles.css script.js contact-form.js server.py mailer.py trust_score.py \
  scripts/google-leads-automation.gs robots.txt sitemap.xml "checkpoints/$NAME/"
# … weitere Dateien nach Bedarf
```

Eintrag in dieser Datei ergänzen.
