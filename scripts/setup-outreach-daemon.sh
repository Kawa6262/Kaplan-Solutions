#!/bin/bash
# Kaplan Solutions — Outreach-Daemon + Sleep-Schutz einrichten
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_SRC="$ROOT/scripts/com.kaplansolutions.outreach.plist"
PLIST_AWAKE_SRC="$ROOT/scripts/com.kaplansolutions.outreach-awake.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.kaplansolutions.outreach.plist"
PLIST_AWAKE_DST="$HOME/Library/LaunchAgents/com.kaplansolutions.outreach-awake.plist"
PYTHON="$(command -v python3)"

chmod +x "$ROOT/scripts/outreach-daemon.sh" "$ROOT/scripts/outreach-keep-awake.sh" 2>/dev/null || true

if [[ ! -f "$ROOT/.env" ]]; then
  echo "⚠️  Keine .env gefunden. Kopiere .env.example nach .env und trage API-Keys ein:"
  echo "   cp $ROOT/.env.example $ROOT/.env"
  exit 1
fi

sed "s|__ROOT__|$ROOT|g; s|__PYTHON__|$PYTHON|g" "$PLIST_SRC" > "$PLIST_DST"
sed "s|__ROOT__|$ROOT|g; s|__PYTHON__|$PYTHON|g" "$PLIST_AWAKE_SRC" > "$PLIST_AWAKE_DST"

launchctl bootout "gui/$(id -u)/com.kaplansolutions.outreach" 2>/dev/null || true
launchctl bootout "gui/$(id -u)/com.kaplansolutions.outreach-awake" 2>/dev/null || true

launchctl bootstrap "gui/$(id -u)" "$PLIST_DST"
launchctl enable "gui/$(id -u)/com.kaplansolutions.outreach"
launchctl kickstart -k "gui/$(id -u)/com.kaplansolutions.outreach"

launchctl bootstrap "gui/$(id -u)" "$PLIST_AWAKE_DST"
launchctl enable "gui/$(id -u)/com.kaplansolutions.outreach-awake"
launchctl kickstart -k "gui/$(id -u)/com.kaplansolutions.outreach-awake"

echo "✅ Outreach-Daemon läuft (Mo–Fr 8–18 Uhr, automatisch)."
echo "   Status:  cd $ROOT && python3 -m outreach.runner status"
echo "   Log:     tail -f $ROOT/data/outreach.log"
echo "   Awake:   tail -f $ROOT/data/outreach-awake.log"
echo ""
echo "   Stoppen:"
echo "     launchctl bootout gui/$(id -u)/com.kaplansolutions.outreach"
echo "     launchctl bootout gui/$(id -u)/com.kaplansolutions.outreach-awake"
echo ""
echo "   Hinweis: Im echten Ruhemodus (Deckel zu, tief schlafen) kann kein Mac"
echo "   E-Mails senden. Nach dem Aufwachen holt das System automatisch nach."
