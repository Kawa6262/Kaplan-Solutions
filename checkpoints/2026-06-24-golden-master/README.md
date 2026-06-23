# Kaplan Solutions — Landing Page

Premium-Website für **Kaplan Solutions** — Bauvermittlung aus Berlin.

## Lokal starten

```bash
~/Documents/KaplanSolutions/start.sh
```

Dann im Browser: **http://localhost:8080**

## E-Mail bei Kontaktanfragen (Admin)

1. Beispiel-Datei kopieren:
   ```bash
   cd ~/Documents/KaplanSolutions
   cp .env.example .env
   ```
2. In `.env` eintragen:
   - `ADMIN_EMAIL` — Ihre E-Mail (empfängt alle Anfragen)
   - `SMTP_USER` / `SMTP_PASS` — Zugangsdaten Ihres Mail-Anbieters

**Gmail:** App-Passwort unter [Google-Konto → Sicherheit](https://myaccount.google.com/apppasswords) erstellen (2-Faktor-Auth nötig).

3. Server neu starten (`start.sh`).

Bei jeder Anfrage erhalten Sie eine E-Mail mit: Anfrageart (Auftraggeber/Auftragnehmer), Name, E-Mail, Telefon, Projektart und Nachricht. Antworten geht direkt per „Antworten“ an den Kunden.

## Dateien

| Datei | Beschreibung |
|---|---|
| `index.html` | Seitenstruktur |
| `styles.css` | Design & Layout |
| `script.js` | Animationen, Navigation, Formular |

## Online veröffentlichen

### Option A — Netlify (kostenlos, empfohlen)
1. Auf [netlify.com](https://netlify.com) anmelden
2. Ordner `KaplanSolutions` per Drag & Drop hochladen
3. Fertig — eigene Domain verbinden unter *Domain settings*

### Option B — GitHub Pages
```bash
cd ~/Documents/KaplanSolutions
git init
git add .
git commit -m "Kaplan Solutions Landing Page"
# Repository auf GitHub erstellen, dann:
git remote add origin https://github.com/IHR-USERNAME/kaplan-solutions.git
git push -u origin main
```
Unter *Settings → Pages → Branch: main* aktivieren.

### Option C — Im lokalen Netzwerk (Handy/Tablet)
```bash
python3 -m http.server 8080 --bind 0.0.0.0
```
Dann auf dem Handy: `http://[Ihre-Mac-IP]:8080`

IP-Adresse herausfinden: `ifconfig | grep "inet "`
