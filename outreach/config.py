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
SEND_HOUR_START = int(os.getenv("OUTREACH_HOUR_START", "7"))
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

# Projekt-Outreach: konkrete Ausschreibung an ausführende Betriebe in der Region
# des Bauvorhabens. Anders als die Partner-Kampagne wirbt sie nicht um eine
# Netzwerk-Mitgliedschaft, sondern bietet einen benannten Auftrag an. Deshalb
# eigene Städte- und Gewerkeliste: Ein Betrieb aus Hamburg nützt bei einem
# Bauvorhaben in Duisburg nichts.
PROJEKT_ENABLED = os.getenv("OUTREACH_PROJEKT_ENABLED", "1").strip().lower() not in (
    "0",
    "false",
    "no",
)
# Suche und Anreicherung laufen sofort, der Versand aber erst nach ausdrücklicher
# Freigabe. Eine Mail, die ein reales Bauvorhaben eines realen Auftraggebers
# nennt, darf nicht durch einen Daemon-Zyklus ausgelöst werden.
PROJEKT_SEND_ENABLED = os.getenv("OUTREACH_PROJEKT_SEND_ENABLED", "0").strip().lower() in (
    "1",
    "true",
    "yes",
)
PROJEKT_DAILY_SEND_LIMIT = int(os.getenv("OUTREACH_PROJEKT_DAILY_LIMIT", "60"))
PROJEKT_DAILY_DISCOVER_LIMIT = int(os.getenv("OUTREACH_PROJEKT_DISCOVER_LIMIT", "200"))
PROJEKT_SEND_BATCH_PER_CYCLE = int(os.getenv("OUTREACH_PROJEKT_SEND_BATCH", "8"))
PROJEKT_DISCOVER_BATCHES_PER_CYCLE = int(os.getenv("OUTREACH_PROJEKT_DISCOVER_BATCH", "4"))

# Ein Betrieb, der vor Kurzem schon eine Mail bekommen hat, darf nicht sofort
# die nächste bekommen.
PROJEKT_MIN_DAYS_SINCE_CONTACT = int(os.getenv("OUTREACH_PROJEKT_MIN_DAYS", "5"))
# Hintergrund-Check: Betriebe mit schlechtem Ruf werden dem Auftraggeber
# nicht vorgeschlagen. Erst ab genug Bewertungen ist das Urteil belastbar.
PROJEKT_MIN_RATING = float(os.getenv("OUTREACH_PROJEKT_MIN_RATING", "3.5"))
PROJEKT_MIN_RATING_COUNT = int(os.getenv("OUTREACH_PROJEKT_MIN_RATING_COUNT", "5"))
PROJEKT_RATING_BATCH = int(os.getenv("OUTREACH_PROJEKT_RATING_BATCH", "12"))

# Umkreis des Bauvorhabens, grob nach Entfernung sortiert.
_PROJEKT_CITIES_ENV = os.getenv("OUTREACH_PROJEKT_CITIES", "").strip()
_DEFAULT_PROJEKT_CITIES = [
    "Duisburg", "Oberhausen", "Mülheim an der Ruhr", "Moers", "Dinslaken",
    "Rheinberg", "Kamp-Lintfort", "Voerde", "Neukirchen-Vluyn", "Krefeld",
    "Essen", "Bottrop", "Ratingen", "Düsseldorf", "Meerbusch", "Willich",
    "Kempen", "Neuss", "Gelsenkirchen", "Wesel", "Bochum", "Herne",
    "Recklinghausen", "Velbert", "Mönchengladbach", "Viersen", "Xanten",
    "Geldern", "Dortmund", "Hilden",
]
PROJEKT_CITIES = [
    c.strip() for c in _PROJEKT_CITIES_ENV.split(",") if c.strip()
] or _DEFAULT_PROJEKT_CITIES

# Reihenfolge ist Absicht: Der Bauherr sucht eine ausführende Firma für alles,
# deshalb zuerst Generalunternehmer und Komplettsanierer, danach Einzelgewerke
# aus dem Leistungsverzeichnis.
_PROJEKT_TRADES_ENV = os.getenv("OUTREACH_PROJEKT_TRADES", "").strip()
_DEFAULT_PROJEKT_TRADES = [
    "Generalunternehmer Bau",
    "Bauunternehmen Sanierung",
    "Schlüsselfertigbau",
    "Komplettsanierung Wohnung",
    "Sanierungsbau Firma",
    "Innenausbau Firma",
    "Trockenbau Firma",
    "Abbruch Rückbau Firma",
    "Badsanierung Firma",
    "SHK Betrieb Heizung Sanitär",
    "Elektroinstallateur Bau",
    "Malerbetrieb",
    "Fliesenleger Betrieb",
    "Bodenleger Parkett",
    "Estrichleger Firma",
    "Fensterbau Montage",
    "Tischlerei Innenausbau",
    "Maurerbetrieb",
    "Brandschutz Fachbetrieb",
    "Garten- und Landschaftsbau",
]
PROJEKT_TRADE_QUERIES = [
    t.strip() for t in _PROJEKT_TRADES_ENV.split(",") if t.strip()
] or _DEFAULT_PROJEKT_TRADES

CAMPAIGN_PARTNER = "partner"
CAMPAIGN_REFERRAL = "referral"
CAMPAIGN_BAUHERR = "bauherr"
CAMPAIGN_PROJEKT = "projekt"


def cities_for(campaign: str) -> list[str]:
    """Suchgebiet je Kampagne. Die Projekt-Kampagne ist an ein Bauvorhaben
    gebunden und darf nicht der bundesweiten Fokusliste folgen."""
    if campaign == CAMPAIGN_PROJEKT:
        return PROJEKT_CITIES
    return GERMAN_CITIES
