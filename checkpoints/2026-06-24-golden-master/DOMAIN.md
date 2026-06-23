# Domain & Online-Stellung — Kaplan Solutions

Anleitung für **kaplan-solutions.de** (oder eine andere Domain Ihrer Wahl) mit **HTTPS** und funktionierendem Kontaktformular.

---

## Übersicht

| Schritt | Was | Dauer |
|--------|-----|-------|
| 1 | Domain kaufen | ~10 Min. |
| 2 | Code auf GitHub | ~15 Min. |
| 3 | Auf Render.com hosten | ~15 Min. |
| 4 | Domain verbinden + SSL | ~10 Min. (+ DNS-Wartezeit bis 48h) |
| 5 | E-Mail & Umgebungsvariablen | ~10 Min. |

**Empfohlener Anbieter Hosting:** [Render.com](https://render.com) (kostenloser Einstieg, automatisches HTTPS, Flask-fähig).

---

## Schritt 1 — Domain kaufen

Registrieren Sie z. B. bei:

- [IONOS](https://www.ionos.de) (deutsch, .de-Domains)
- [Strato](https://www.strato.de)
- [Cloudflare Registrar](https://www.cloudflare.com/products/registrar/)

**Gewünschter Name:** `kaplan-solutions.de` (falls frei).

Notieren Sie Zugang zum **DNS-Verwaltungsbereich** — den brauchen Sie in Schritt 4.

---

## Schritt 2 — Projekt auf GitHub

Im Terminal:

```bash
cd ~/Documents/KaplanSolutions
git init
git add .
git commit -m "Kaplan Solutions Website — Produktionsversion"
```

Erstellen Sie auf [github.com](https://github.com) ein **neues privates Repository** (z. B. `kaplan-solutions`).

```bash
git remote add origin https://github.com/IHR-USERNAME/kaplan-solutions.git
git branch -M main
git push -u origin main
```

> Wichtig: `.env` wird **nicht** mit hochgeladen (steht in `.gitignore`). Passwörter nur im Hosting-Dashboard eintragen.

---

## Schritt 3 — Auf Render deployen

1. Konto auf [render.com](https://render.com) anlegen (GitHub verbinden).
2. **New → Web Service**
3. Repository `kaplan-solutions` wählen
4. Einstellungen:
   - **Name:** `kaplan-solutions`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn server:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
   - **Plan:** Free (zum Testen)

5. Unter **Environment** alle Werte aus Ihrer lokalen `.env` eintragen:

| Variable | Beispiel |
|----------|----------|
| `ADMIN_EMAIL` | Kawa.f.Kaplan@gmail.com |
| `SMTP_HOST` | smtp.gmail.com |
| `SMTP_PORT` | 587 |
| `SMTP_USER` | … |
| `SMTP_PASS` | Gmail App-Passwort |
| `FROM_EMAIL` | … |
| `REPLY_EMAIL` | Kawa.f.Kaplan@gmail.com |
| `COMPANY_PHONE` | +49 159 01309199 |
| `COMPANY_LEGAL_FORM` | privat |
| `COMPANY_OPERATOR` | Ferhat Kawa Kaplan |
| `COMPANY_STREET` | Hochstraße 8 |
| `COMPANY_ZIP` | 13357 |
| `COMPANY_CITY` | Berlin |
| `COMPANY_WEBSITE` | https://kaplan-solutions.de |

6. **Create Web Service** — nach ein paar Minuten erhalten Sie eine URL wie  
   `https://kaplan-solutions.onrender.com`

Testen Sie das Kontaktformular dort.

---

## Schritt 4 — Domain verbinden (HTTPS automatisch)

1. Im Render-Dashboard: Ihr Service → **Settings** → **Custom Domains**
2. **Add Custom Domain:** `kaplan-solutions.de`
3. Optional auch: `www.kaplan-solutions.de`
4. Render zeigt DNS-Einträge an, z. B.:

| Typ | Name | Ziel |
|-----|------|------|
| `CNAME` | `www` | `kaplan-solutions.onrender.com` |
| `A` oder `ALIAS` | `@` | (IP/Anleitung von Render) |

5. Diese Einträge bei Ihrem Domain-Anbieter (IONOS/Strato/…) eintragen.
6. Warten (oft 15 Min. – 48 Std.), bis DNS weltweit aktiv ist.
7. Render stellt **kostenloses SSL (HTTPS)** automatisch aus.

**Prüfen:** https://kaplan-solutions.de im Browser öffnen.

---

## Schritt 5 — www weiterleiten (empfohlen)

Entweder nur `www` nutzen oder nur die Root-Domain — Render kann beide eintragen und leitet um.

In IONOS/Strato: Weiterleitung `www` → Hauptdomain oder umgekehrt einstellen.

---

## Checkliste nach Go-Live

- [ ] Startseite lädt mit HTTPS (Schloss-Symbol)
- [ ] Impressum / Datenschutz / AGB erreichbar
- [ ] Kontaktformular sendet E-Mail
- [ ] Kunde erhält Bestätigungsmail
- [ ] Firmensitz in Impressum korrekt
- [ ] Cookie-Hinweis sichtbar

---

## Kosten (Richtwerte)

| Posten | ca. |
|--------|-----|
| Domain `.de` | 5–15 € / Jahr |
| Render Free | 0 € (mit Einschränkungen, z. B. Kaltstart) |
| Render Paid | ab ~7 $ / Monat (empfohlen für Kundenwebsite) |

---

## Hilfe

- Render-Dokumentation: https://render.com/docs/custom-domains  
- DNS-Probleme: beim Domain-Anbieter prüfen, ob CNAME/A-Record korrekt gesetzt ist  
- Formular ohne E-Mail: SMTP-Variablen im Render-Dashboard prüfen

Wenn Sie möchten, können wir im nächsten Schritt **gemeinsam GitHub + Render** einrichten — sagen Sie Bescheid, ob die Domain schon gekauft ist und wie sie heißen soll.
