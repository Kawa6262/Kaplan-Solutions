#!/bin/bash
# Kaplan Solutions — Outreach-Daemon + Sleep-Schutz + Health + Watchdog
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_SRC="$ROOT/scripts/com.kaplansolutions.outreach.plist"
PLIST_AWAKE_SRC="$ROOT/scripts/com.kaplansolutions.outreach-awake.plist"
PLIST_HEALTH_SRC="$ROOT/scripts/com.kaplansolutions.outreach-health.plist"
PLIST_WATCHDOG_SRC="$ROOT/scripts/com.kaplansolutions.outreach-watchdog.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.kaplansolutions.outreach.plist"
PLIST_AWAKE_DST="$HOME/Library/LaunchAgents/com.kaplansolutions.outreach-awake.plist"
PLIST_HEALTH_DST="$HOME/Library/LaunchAgents/com.kaplansolutions.outreach-health.plist"
PLIST_WATCHDOG_DST="$HOME/Library/LaunchAgents/com.kaplansolutions.outreach-watchdog.plist"
PYTHON="$(command -v python3)"

chmod +x "$ROOT/scripts/outreach-daemon.sh" "$ROOT/scripts/outreach-keep-awake.sh" "$ROOT/scripts/setup-mac-outreach-power.sh" 2>/dev/null || true

if [[ ! -f "$ROOT/.env" ]]; then
  echo "⚠️  Keine .env gefunden. Kopiere .env.example nach .env und trage API-Keys ein:"
  echo "   cp $ROOT/.env.example $ROOT/.env"
  exit 1
fi

sed "s|__ROOT__|$ROOT|g; s|__PYTHON__|$PYTHON|g" "$PLIST_SRC" > "$PLIST_DST"
sed "s|__ROOT__|$ROOT|g; s|__PYTHON__|$PYTHON|g" "$PLIST_AWAKE_SRC" > "$PLIST_AWAKE_DST"
sed "s|__ROOT__|$ROOT|g; s|__PYTHON__|$PYTHON|g" "$PLIST_HEALTH_SRC" > "$PLIST_HEALTH_DST"
sed "s|__ROOT__|$ROOT|g; s|__PYTHON__|$PYTHON|g" "$PLIST_WATCHDOG_SRC" > "$PLIST_WATCHDOG_DST"

# .env in Plists injizieren — LaunchAgent darf iCloud/.env oft nicht lesen
"$PYTHON" << PYEOF
import plistlib
from pathlib import Path

root = Path("$ROOT")
env = {}
for line in (root / ".env").read_text(encoding="utf-8", errors="replace").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    k, v = k.strip(), v.strip().strip('"').strip("'")
    if k:
        env[k] = v

for plist_path in (
    Path("$PLIST_DST"),
    Path("$PLIST_HEALTH_DST"),
    Path("$PLIST_WATCHDOG_DST"),
):
    with plist_path.open("rb") as f:
        plist = plistlib.load(f)
    base = dict(plist.get("EnvironmentVariables") or {})
    base.update(env)
    plist["EnvironmentVariables"] = base
    with plist_path.open("wb") as f:
        plistlib.dump(plist, f)
print(f"   Env: {len(env)} Variablen in LaunchAgents eingetragen")
PYEOF

launchctl bootout "gui/$(id -u)/com.kaplansolutions.outreach" 2>/dev/null || true
launchctl bootout "gui/$(id -u)/com.kaplansolutions.outreach-awake" 2>/dev/null || true
launchctl bootout "gui/$(id -u)/com.kaplansolutions.outreach-health" 2>/dev/null || true
launchctl bootout "gui/$(id -u)/com.kaplansolutions.outreach-watchdog" 2>/dev/null || true

launchctl bootstrap "gui/$(id -u)" "$PLIST_DST"
launchctl enable "gui/$(id -u)/com.kaplansolutions.outreach"
launchctl kickstart -k "gui/$(id -u)/com.kaplansolutions.outreach"

launchctl bootstrap "gui/$(id -u)" "$PLIST_AWAKE_DST"
launchctl enable "gui/$(id -u)/com.kaplansolutions.outreach-awake"
launchctl kickstart -k "gui/$(id -u)/com.kaplansolutions.outreach-awake"

launchctl bootstrap "gui/$(id -u)" "$PLIST_HEALTH_DST"
launchctl enable "gui/$(id -u)/com.kaplansolutions.outreach-health"

launchctl bootstrap "gui/$(id -u)" "$PLIST_WATCHDOG_DST"
launchctl enable "gui/$(id -u)/com.kaplansolutions.outreach-watchdog"

echo "✅ Outreach-Daemon läuft (Mo–Fr 8–18 Uhr)."
echo "✅ Health-Check: Mo–Fr 8:30 Uhr"
echo "✅ Watchdog: Mo–Fr 10 / 13 / 15 / 17 Uhr"
echo ""
echo "   WICHTIG für Deckel zu: einmalig ausführen:"
echo "     sudo bash $ROOT/scripts/setup-mac-outreach-power.sh"
echo ""
echo "   Status:  cd $ROOT && python3 -m outreach.runner status"
