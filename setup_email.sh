#!/bin/bash
# Gmail für Kontaktanfragen einrichten (Dialog auf dem Mac)
cd "$(dirname "$0")"

echo ""
echo "  Kaplan Solutions — E-Mail einrichten"
echo "  -------------------------------------"
echo "  Es öffnet sich ein Dialog für Ihre Gmail-Adresse"
echo "  und Ihr App-Passwort (Google-Konto → Sicherheit → App-Passwörter)."
echo ""

EMAIL=$(osascript <<'APPLESCRIPT'
tell application "System Events"
    activate
end tell
display dialog "Ihre Gmail-Adresse (empfängt alle Anfragen):" default answer "" buttons {"Abbrechen", "Weiter"} default button "Weiter" with title "Kaplan Solutions"
return text returned of result
APPLESCRIPT
)

if [ -z "$EMAIL" ]; then
    echo "Abgebrochen."
    exit 1
fi

PASS=$(osascript <<'APPLESCRIPT'
tell application "System Events"
    activate
end tell
display dialog "Gmail App-Passwort (16 Zeichen, ohne Leerzeichen):" default answer "" with hidden answer buttons {"Abbrechen", "Speichern"} default button "Speichern" with title "Kaplan Solutions"
return text returned of result
APPLESCRIPT
)

if [ -z "$PASS" ]; then
    echo "Abgebrochen."
    exit 1
fi

# Leerzeichen aus App-Passwort entfernen
PASS=$(echo "$PASS" | tr -d ' ')

cat > .env <<EOF
ADMIN_EMAIL=${EMAIL}
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=${EMAIL}
SMTP_PASS=${PASS}
FROM_EMAIL=${EMAIL}
PORT=8080
EOF

chmod 600 .env

echo ""
echo "  ✓  Gespeichert in .env"
echo "  ✓  Anfragen gehen an: ${EMAIL}"
echo ""
echo "  Server neu starten: ./start.sh"
echo ""
