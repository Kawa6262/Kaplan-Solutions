# Kaplan Solutions — Umsetzungs-Roadmap

Schritt für Schritt. Jeder Punkt wird vollständig abgeschlossen, bevor der nächste beginnt.

| # | Schritt | Status |
|---|---------|--------|
| 1 | Impressum, Datenschutz, AGB + DSGVO-Checkbox | ✅ Erledigt |
| 2 | Cookie-/Tracking-Hinweis (kein Tracking, Info-Banner) | ✅ Erledigt |
| 3 | Referenzen / Case Studies | ✅ Erledigt |
| 4 | Testimonials | ⏭ Übersprungen |
| 5 | „So läuft's in 24h“ am Formular | ✅ Erledigt |
| 6 | Telefon-CTA prominent | ⏭ Übersprungen |
| 7 | WhatsApp-Button (optional) | ⏭ Übersprungen |
| 8 | Online stellen + Domain + HTTPS | 🔄 Vorbereitet — siehe `DOMAIN.md` |
| 9 | Professionelle E-Mail-Adresse | ⏳ Offen |
| 10 | Spam-Schutz (Honeypot / Rate-Limit) | ⏳ Offen |
| 11 | Admin-Übersicht Anfragen | ⏳ Offen |
| 12 | SEO (Meta, Schema, Sitemap) | ⏳ Offen |
| 13 | Lokale SEO-Texte | ⏳ Offen |
| 14 | Blog/Ratgeber | ⏳ Offen |
| 15 | Performance (WebP, lazy load) | ⏳ Offen |
| 16 | Favicon + Open Graph | ⏳ Offen |
| 17 | 404-Seite | ⏳ Offen |
| 18 | Lead-Scoring in Admin-Mail | ⏳ Offen |
| 19 | CRM-Anbindung | ⏳ Offen |
| 20 | Kalender-Link in Bestätigungsmail | ⏳ Offen |

## Schritt 1 — Was Sie noch tun sollten

**Status:** Noch keine Firma gegründet, Standort Berlin (`COMPANY_LEGAL_FORM=privat`).

Tragen Sie in Ihrer `.env` ein (siehe `.env.example`):

- `COMPANY_OPERATOR` — Ihr vollständiger Name (Pflicht fürs Impressum)
- `COMPANY_STREET` + `COMPANY_ZIP` + `COMPANY_CITY` — Ihre Berliner Adresse (Pflicht fürs Impressum)

Nach Firmengründung: `COMPANY_LEGAL_FORM` auf `einzelunternehmen` oder `gmbh` ändern und Registerdaten ergänzen.
