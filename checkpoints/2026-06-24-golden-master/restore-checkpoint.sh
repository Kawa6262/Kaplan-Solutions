#!/bin/bash
# Stellt einen gespeicherten Kontrollpunkt wieder her.
# Nutzung: ./restore-checkpoint.sh [checkpoint-name]

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
DEFAULT="2026-06-24-golden-master"
CP="${1:-$DEFAULT}"
SRC="$ROOT/checkpoints/$CP"

if [[ ! -d "$SRC" ]]; then
    echo "Checkpoint nicht gefunden: $CP"
    echo ""
    echo "Verfügbare Kontrollpunkte:"
    ls -1 "$ROOT/checkpoints" 2>/dev/null || echo "  (keine)"
    exit 1
fi

echo "Wiederherstellen: $CP"
echo "Quelle: $SRC"
echo ""
read -r -p "Aktuelle Dateien werden überschrieben. Fortfahren? [j/N] " confirm
if [[ ! "$confirm" =~ ^[jJyY]$ ]]; then
    echo "Abgebrochen."
    exit 0
fi

rsync -a --delete \
    --exclude='MANIFEST.txt' \
    "$SRC/" "$ROOT/"

echo ""
echo "Fertig. Projekt wurde auf Kontrollpunkt '$CP' zurückgesetzt."
if [[ "$CP" == "2026-06-24-golden-master" ]]; then
  echo ""
  echo "★ Golden Master wiederhergestellt — siehe GOLDEN-MASTER.md"
fi
echo "Server neu starten: cd \"$ROOT\" && ./start.sh"
