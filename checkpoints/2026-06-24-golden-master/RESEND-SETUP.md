# E-Mails nicht mehr im Spam — Resend + kaplan-solutions.de

**Problem:** Mails von `onboarding@resend.dev` landen im Spam.  
**Lösung:** Eigene Domain bei Resend verifizieren → Absender `kontakt@kaplan-solutions.de`.

---

## Schritt 1 — Domain bei Resend hinzufügen

1. Einloggen auf [resend.com](https://resend.com)
2. Links **Domains** → **Add Domain**
3. Domain eingeben: `kaplan-solutions.de`
4. Resend zeigt DNS-Einträge (meist 3× TXT für DKIM + 1× TXT/MX für SPF)

---

## Schritt 2 — DNS bei Strato eintragen

1. [Strato Kunden-Login](https://www.strato.de) → Domain **kaplan-solutions.de** → **DNS-Verwaltung**
2. Für **jeden** Eintrag, den Resend anzeigt, einen neuen DNS-Record anlegen:

| Typ | Name/Host | Wert (von Resend kopieren) |
|-----|-----------|----------------------------|
| TXT | `resend._domainkey` (Beispiel) | langer DKIM-String |
| TXT | `@` oder leer | SPF-Eintrag von Resend |
| ggf. MX | `send` | von Resend |

3. Speichern — Verifizierung dauert oft **15 Min. bis 48 Std.**

4. In Resend auf **Verify** klicken → Status muss **Verified** werden ✅

---

## Schritt 3 — Render Environment anpassen

Render → **Kaplan-Solutions** → **Environment** → setzen/ändern:

| Variable | Wert |
|----------|------|
| `RESEND_FROM` | `Kaplan Solutions <kontakt@kaplan-solutions.de>` |
| `REPLY_EMAIL` | `Kawa.f.Kaplan@gmail.com` (oder später echtes Postfach) |
| `ADMIN_EMAIL` | `Kawa.f.Kaplan@gmail.com` |

**Save Changes** → Render startet neu.

> Der Code nutzt bereits `kontakt@kaplan-solutions.de` als Standard-Absender.  
> Ohne verifizierte Domain schlagen Mails fehl — deshalb zuerst Schritt 1+2!

---

## Schritt 4 — Test

1. Test-Anfrage über https://kaplan-solutions.de senden
2. Bestätigungs-Mail im Posteingang prüfen (nicht Spam)
3. Absender sollte **Kaplan Solutions &lt;kontakt@kaplan-solutions.de&gt;** sein

---

## Optional — DMARC (empfohlen)

In Strato zusätzlich TXT-Record:

| Name | Wert |
|------|------|
| `_dmarc` | `v=DMARC1; p=none; rua=mailto:Kawa.f.Kaplan@gmail.com` |

Später auf `p=quarantine` erhöhen, wenn alles stabil läuft.
