# Kontrollpunkte — Kaplan Solutions

Gespeicherte Versionen des Projekts, auf die Sie jederzeit zurückspringen können.

## Aktueller Kontrollpunkt

| Name | Datum | Beschreibung |
|------|-------|--------------|
| `2026-06-02-lead-system-komplett` | 02.06.2026 | **Aktuell (vor Intelligence-Upgrade)** — Alles live: Anfrage-Nr., Sheet-Sortierung, Drive-Ordner, Partner-Matching in Mails, Webhook-Fix (25s Timeout). Siehe `checkpoints/2026-06-02-lead-system-komplett/KONFIGURATION.txt` |
| `2026-05-31-mails-komplett-verifiziert` | 31.05.2026 | Domain verifiziert (SPF+DKIM+DMARC), Absender `kontakt@kaplan-solutions.de`, schöne Lead- + Kunden-Mails, Sicherheitsnetz FormSubmit |
| `2026-05-29-resend-funktioniert` | 29.05.2026 | Resend live (Cloudflare-Fix + korrekte ADMIN_EMAIL), schöne Lead-Mail, Rollenwahl, Sicherheitsnetz FormSubmit |
| `2026-05-26-formular-funktioniert` | 26.05.2026 | FormSubmit live, Rollenwahl, professionelle Lead- + Bestätigungs-Mails |
| `2026-05-19-alles-funktioniert` | 19.05.2026 | Formular, Rechtsseiten, Firmensitz Berlin, DSGVO, E-Mail |
| `2026-05-19-kontaktformular-funktioniert` | 19.05.2026 | Älter — nur Formular + E-Mail (ohne Rechtsseiten/Berlin) |

## Wiederherstellen

```bash
cd ~/Documents/KaplanSolutions
./restore-checkpoint.sh
```

Oder einen bestimmten Kontrollpunkt:

```bash
./restore-checkpoint.sh 2026-05-19-alles-funktioniert
```

Danach Server neu starten:

```bash
./start.sh
```

## Was gespeichert wird

- `index.html`, `styles.css`, `script.js`, `server.py`
- `start.sh`, `setup_email.sh`, `requirements.txt`, `README.md`
- `assets/` (Bilder)

## Was nicht gespeichert wird

- `.env` — Ihre E-Mail-Zugangsdaten bleiben unverändert
- `venv/` — Python-Umgebung (nach Restore ggf. `./start.sh` erneut ausführen)
- `data/inbox/` — eingegangene Anfragen

## Neuen Kontrollpunkt anlegen

Wenn eine Version wieder stabil läuft, Kopie anlegen:

```bash
NAME="2026-05-20-meine-beschreibung"
mkdir -p "checkpoints/$NAME"
rsync -a --exclude='venv' --exclude='.env' --exclude='data' --exclude='checkpoints' \
  index.html styles.css script.js server.py start.sh setup_email.sh \
  requirements.txt .env.example .gitignore README.md "checkpoints/$NAME/"
rsync -a assets/ "checkpoints/$NAME/assets/"
```

Eintrag in dieser Datei ergänzen.
