#!/bin/bash
# Mac am Netzteil wach halten (Deckel zu + Ladekabel = Outreach kann laufen)
# Einmalig mit sudo ausführen: sudo bash scripts/setup-mac-outreach-power.sh
set -euo pipefail

echo "=== Mac Power für Outreach (Netzteil) ==="
echo "Verhindert Sleep am Ladekabel — wichtig bei geschlossenem Deckel."
echo ""

pmset -c sleep 0
pmset -c disksleep 0
pmset -c displaysleep 10

echo ""
echo "Aktuelle Einstellungen (Netzteil -c):"
pmset -g custom | sed -n '/AC Power/,/Battery Power/p' | head -20
echo ""
echo "✅ Mac schläft am Netzteil nicht mehr ein (nur Display dimmt nach 10 Min)."
echo "   Wichtig: Ladekabel muss angeschlossen sein wenn Deckel zu ist."
