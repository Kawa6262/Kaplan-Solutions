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

# Zuverlässigkeit: Mac wach halten + Nachholversand nach Sleep
CAFFEINATE_ENABLED = os.getenv("OUTREACH_CAFFEINATE", "1").strip().lower() not in (
    "0",
    "false",
    "no",
)
WAKE_CATCHUP_ENABLED = os.getenv("OUTREACH_WAKE_CATCHUP", "1").strip().lower() not in (
    "0",
    "false",
    "no",
)

# Versand nur werktags 08:00–18:00 Europe/Berlin
SEND_HOUR_START = int(os.getenv("OUTREACH_HOUR_START", "8"))
SEND_HOUR_END = int(os.getenv("OUTREACH_HOUR_END", "18"))
SEND_WEEKDAYS_ONLY = os.getenv("OUTREACH_WEEKDAYS_ONLY", "1").strip() not in ("0", "false", "no")

SHEET_SYNC_BATCH = int(os.getenv("OUTREACH_SHEET_SYNC_BATCH", "5"))

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

_DEFAULT_TRADES = [
    "Generalunternehmer Bau",
    "Bauunternehmen",
    "Sanierungsbau Firma",
    "Tiefbau Unternehmen",
    "SHK Betrieb Heizung Sanitär",
    "Elektroinstallateur Bau",
    "Dachdecker Betrieb",
    "Trockenbau Firma",
    "Estrichleger Firma",
    "Fliesenleger Betrieb",
    "Malerbetrieb",
    "Garten- und Landschaftsbau",
    "Zimmerei Holzbau",
    "Gerüstbau Firma",
    "Betonbau Stahlbetonbau",
    "Fensterbau Montage",
    "Innenausbau Firma",
    "Klempnerei Spengler",
    "Bodenleger Parkett",
    "Stuckateur Verputzer",
    "Abbruchunternehmen",
    "Pflasterbau Straßenbau",
    "Rohbau Firma",
    "Schlüsselfertigbau",
    "Wärmedämmung Fassade",
    "Bauschlosserei Metallbau",
]

_TRADE_ENV = os.getenv("OUTREACH_PARTNER_TRADES", "").strip()
TRADE_QUERIES = (
    [t.strip() for t in _TRADE_ENV.split(",") if t.strip()]
    if _TRADE_ENV
    else _DEFAULT_TRADES
)

PREFERRED_EMAIL_PREFIXES = (
    "info", "kontakt", "contact", "office", "buero", "mail", "anfrage",
    "service", "projekt", "projekte", "auftrag", "vertrieb", "sales",
)

SKIP_EMAIL_DOMAINS = {
    "example.com", "sentry.io", "wixpress.com", "wordpress.com",
    "squarespace.com", "jimdo.com", "ionos.de", "strato.de",
}

# Referral-Outreach: Makler, Architekten, Projektentwickler (B2B-Empfehlungspartner)
REFERRAL_ENABLED = os.getenv("OUTREACH_REFERRAL_ENABLED", "1").strip().lower() not in (
    "0",
    "false",
    "no",
)
REFERRAL_DAILY_SEND_LIMIT = int(os.getenv("OUTREACH_REFERRAL_DAILY_LIMIT", "15"))
REFERRAL_DAILY_DISCOVER_LIMIT = int(os.getenv("OUTREACH_REFERRAL_DISCOVER_LIMIT", "80"))
REFERRAL_SEND_BATCH_PER_CYCLE = int(os.getenv("OUTREACH_REFERRAL_SEND_BATCH", "3"))
REFERRAL_DISCOVER_BATCHES_PER_CYCLE = int(os.getenv("OUTREACH_REFERRAL_DISCOVER_BATCH", "2"))

_REFERRAL_TRADES = os.getenv(
    "OUTREACH_REFERRAL_TRADES",
    "Immobilienmakler,Architekturbüro,Projektentwickler,Immobilienverwaltung,Bauplanungsbüro",
).strip()
REFERRAL_TRADE_QUERIES = [t.strip() for t in _REFERRAL_TRADES.split(",") if t.strip()] or [
    "Immobilienmakler",
    "Architekturbüro",
    "Projektentwickler",
    "Immobilienverwaltung",
    "Ingenieurbüro Tragwerksplanung",
    "Bauplanungsbüro",
]

# Bauherr-Outreach: Projektentwickler, Bauträger, Ingenieurbüros (potenzielle Auftraggeber)
BAUHERR_ENABLED = os.getenv("OUTREACH_BAUHERR_ENABLED", "1").strip().lower() not in (
    "0",
    "false",
    "no",
)
BAUHERR_DAILY_SEND_LIMIT = int(os.getenv("OUTREACH_BAUHERR_DAILY_LIMIT", "15"))
BAUHERR_DAILY_DISCOVER_LIMIT = int(os.getenv("OUTREACH_BAUHERR_DISCOVER_LIMIT", "60"))
BAUHERR_SEND_BATCH_PER_CYCLE = int(os.getenv("OUTREACH_BAUHERR_SEND_BATCH", "3"))
BAUHERR_DISCOVER_BATCHES_PER_CYCLE = int(os.getenv("OUTREACH_BAUHERR_DISCOVER_BATCH", "2"))

_BAUHERR_TRADES = os.getenv(
    "OUTREACH_BAUHERR_TRADES",
    "Projektentwickler,Bauträger,Immobilienentwickler,Ingenieurbüro Bau,Generalplaner,Projektsteuerer Bau,Wohnungsbau",
).strip()
BAUHERR_TRADE_QUERIES = [t.strip() for t in _BAUHERR_TRADES.split(",") if t.strip()] or [
    "Projektentwickler",
    "Bauträger",
    "Immobilienentwickler",
    "Ingenieurbüro Bau",
]

CAMPAIGN_PARTNER = "partner"
CAMPAIGN_REFERRAL = "referral"
CAMPAIGN_BAUHERR = "bauherr"
