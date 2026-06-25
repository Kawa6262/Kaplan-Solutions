#!/bin/bash
# Kaplan Solutions — Outreach-Daemon als macOS-Hintergrunddienst einrichten
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_SRC="$ROOT/scripts/com.kaplansolutions.outreach.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.kaplansolutions.outreach.plist"
PYTHON="$(command -v python3)"

if [[ ! -f "$ROOT/.env" ]]; then
  echo "⚠️  Keine .env gefunden. Kopiere .env.example nach .env und trage API-Keys ein:"
  echo "   cp $ROOT/.env.example $ROOT/.env"
  exit 1
fi

# Platzhalter in plist ersetzen
sed "s|__ROOT__|$ROOT|g; s|__PYTHON__|$PYTHON|g" "$PLIST_SRC" > "$PLIST_DST"

launchctl bootout "gui/$(id -u)/com.kaplansolutions.outreach" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_DST"
launchctl enable "gui/$(id -u)/com.kaplansolutions.outreach"
launchctl kickstart -k "gui/$(id -u)/com.kaplansolutions.outreach"

echo "✅ Outreach-Daemon läuft im Hintergrund."
echo "   Status:  cd $ROOT && python3 -m outreach.runner status"
echo "   Log:     tail -f $ROOT/data/outreach.log"
echo "   Stoppen: launchctl bootout gui/$(id -u)/com.kaplansolutions.outreach"
