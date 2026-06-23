#!/bin/bash
cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "Erstelle virtuelle Umgebung …"
    python3 -m venv venv
    ./venv/bin/pip install -q -r requirements.txt
fi

if [ ! -f ".env" ]; then
    echo ""
    echo "  ⚠  Keine .env gefunden!"
    echo "     cp .env.example .env"
    echo "     Dann ADMIN_EMAIL und SMTP-Daten eintragen."
    echo ""
fi

PORT="${PORT:-8080}"
echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║   Kaplan Solutions — Website gestartet   ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""
echo "  → Browser:  http://localhost:$PORT"
echo "  → Beenden:  Ctrl + C"
echo ""

./venv/bin/python server.py
