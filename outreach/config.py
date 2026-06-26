"""Konfiguration für den Outreach-Daemon."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "outreach.db"
LOG_PATH = DATA_DIR / "outreach.log"

# Tageslimit — bei neuer Domain zuerst 30–40/Tag (Warm-up), dann steigern.
DAILY_SEND_LIMIT = int(os.getenv("OUTREACH_DAILY_LIMIT", "40"))
DAILY_DISCOVER_LIMIT = int(os.getenv("OUTREACH_DISCOVER_LIMIT", "200"))
ENRICH_BATCH = int(os.getenv("OUTREACH_ENRICH_BATCH", "30"))
SEND_BATCH_PER_CYCLE = int(os.getenv("OUTREACH_SEND_BATCH", "8"))
DISCOVER_BATCHES_PER_CYCLE = int(os.getenv("OUTREACH_DISCOVER_BATCH", "3"))

# Pause zwischen Zyklen im Daemon-Modus (Sekunden)
DAEMON_INTERVAL = int(os.getenv("OUTREACH_INTERVAL", "300"))  # 5 Min.

# Versand nur werktags 09:00–18:00 Europe/Berlin
SEND_HOUR_START = int(os.getenv("OUTREACH_HOUR_START", "9"))
SEND_HOUR_END = int(os.getenv("OUTREACH_HOUR_END", "18"))
SEND_WEEKDAYS_ONLY = os.getenv("OUTREACH_WEEKDAYS_ONLY", "1").strip() not in ("0", "false", "no")

GOOGLE_PLACES_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "").strip()

# Suchrotation: Gewerke × Städte
# OUTREACH_FOCUS_CITIES=Berlin → nur Berlin (gut für den Start); leer = ganz Deutschland
_FOCUS = os.getenv("OUTREACH_FOCUS_CITIES", "Berlin,Potsdam").strip()

_ALL_CITIES = [
    "Berlin", "Hamburg", "München", "Köln", "Frankfurt am Main", "Stuttgart",
    "Düsseldorf", "Leipzig", "Dortmund", "Essen", "Bremen", "Dresden",
    "Hannover", "Nürnberg", "Duisburg", "Bochum", "Wuppertal", "Bielefeld",
    "Bonn", "Münster", "Mannheim", "Karlsruhe", "Augsburg", "Wiesbaden",
    "Gelsenkirchen", "Aachen", "Mönchengladbach", "Braunschweig", "Kiel",
    "Chemnitz", "Magdeburg", "Freiburg im Breisgau", "Krefeld", "Mainz",
    "Lübeck", "Erfurt", "Oberhausen", "Rostock", "Kassel", "Hagen",
    "Potsdam", "Saarbrücken", "Hamm", "Oldenburg", "Osnabrück", "Heidelberg",
    "Darmstadt", "Regensburg", "Ingolstadt", "Würzburg", "Ulm", "Heilbronn",
    "Pforzheim", "Göttingen", "Reutlingen", "Koblenz", "Jena", "Trier",
    "Erlangen", "Moers", "Siegen", "Hildesheim", "Salzgitter", "Cottbus",
    "Gütersloh", "Wolfsburg", "Schwerin", "Düren", "Esslingen am Neckar",
    "Ludwigsburg", "Iserlohn", "Tübingen", "Flensburg", "Villingen-Schwenningen",
    "Gießen", "Marburg", "Konstanz", "Neuss", "Viersen", "Delmenhorst",
    "Brandenburg an der Havel", "Aschaffenburg", "Plauen", "Neumünster",
    "Fulda", "Rosenheim", "Landshut", "Bamberg", "Bayreuth", "Celle",
    "Lüneburg", "Passau", "Stralsund", "Weimar", "Gera", "Dessau-Roßlau",
]

if _FOCUS:
    GERMAN_CITIES = [c.strip() for c in _FOCUS.split(",") if c.strip()]
else:
    GERMAN_CITIES = _ALL_CITIES

TRADE_QUERIES = [
    "Bauunternehmen",
    "Generalunternehmer Bau",
    "Tiefbau Unternehmen",
    "Sanierungsbau Firma",
    "Malerbetrieb",
    "Dachdecker Betrieb",
    "Elektroinstallateur Bau",
    "SHK Betrieb Heizung Sanitär",
    "Fliesenleger Betrieb",
    "Estrichleger Firma",
    "Trockenbau Firma",
    "Garten- und Landschaftsbau",
]

PREFERRED_EMAIL_PREFIXES = (
    "info", "kontakt", "contact", "office", "buero", "mail", "anfrage",
    "service", "projekt", "projekte", "auftrag", "vertrieb", "sales",
)

SKIP_EMAIL_DOMAINS = {
    "example.com", "sentry.io", "wixpress.com", "wordpress.com",
    "squarespace.com", "jimdo.com", "ionos.de", "strato.de",
}
