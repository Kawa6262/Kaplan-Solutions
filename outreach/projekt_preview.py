"""Vorschau der Projekt-Ausschreibung, bevor sie an Betriebe rausgeht.

Eine Mail über ein echtes Bauvorhaben eines echten Auftraggebers geht nicht
ungesehen raus. Der Befehl schreibt je Empfängertyp eine HTML- und eine
Textdatei nach data/preview/ und prüft, dass der Auftraggeber nirgends
durchsickert.
"""

from __future__ import annotations

import re
import webbrowser
from pathlib import Path

from outreach.projekt import AKTUELL
from outreach.projekt_templates import build_bodies, build_subject

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "preview"

# Diese Begriffe dürfen in keiner Mail auftauchen. Wer den Auftraggeber kennt,
# kann die Vermittlung umgehen.
VERTRAULICH = (
    "BKI",
    "Biskup",
    "bki-gruppe",
    "Kardinal-Galen",
    "Prinzenstra",
    "St-Anna-Weg",
    "drive.google.com",
)

BEISPIELE = [
    ("Generalunternehmer Bau", "Musterbau GmbH", "Duisburg"),
    ("SHK Betrieb Heizung Sanitär", "Beispiel Haustechnik GmbH", "Oberhausen"),
    ("Elektroinstallateur Bau", "Beispiel Elektro GmbH", "Moers"),
    ("Malerbetrieb", "Beispiel Maler GmbH", "Krefeld"),
]


def _check_leak(text: str, html: str, label: str) -> list[str]:
    # Wortgrenzen, sonst schlägt "BKI" im CSS-Präfix "-webkit-" an.
    haystack = f"{text}\n{html}"
    found = []
    for word in VERTRAULICH:
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(word)}", haystack, re.IGNORECASE):
            found.append(word)
    return found


def write_preview(open_browser: bool = True) -> list[Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    leaks: list[str] = []

    for trade, company, city in BEISPIELE:
        subject = build_subject(company, city)
        text, html = build_bodies(
            company, city, trade, recipient_email="beispiel@example.de", prospect_id=1
        )
        found = _check_leak(text, html, trade)
        if found:
            leaks.append(f"{trade}: {', '.join(found)}")

        slug = trade.split()[0].lower().replace("ü", "ue").replace("ä", "ae")
        html_path = OUT / f"projekt-{slug}.html"
        html_path.write_text(html, encoding="utf-8")
        text_path = OUT / f"projekt-{slug}.txt"
        text_path.write_text(f"BETREFF: {subject}\n\n{text}", encoding="utf-8")
        written += [html_path, text_path]

        print(f"\n{'=' * 72}")
        print(f"GEWERK:  {trade}  ({company}, {city})")
        print(f"BETREFF: {subject}")
        print(f"{'=' * 72}")
        print(text)

    print(f"\n{'=' * 72}")
    print(f"Ausschreibung {AKTUELL.referenz} — {AKTUELL.region}")
    print(f"Objekte: {len(AKTUELL.objekte)}, Einheiten: {AKTUELL.einheiten_gesamt}, "
          f"Volumen: {AKTUELL.volumen_gesamt:,} EUR brutto".replace(",", "."))
    if leaks:
        print("\nWARNUNG — vertrauliche Angaben in der Mail gefunden:")
        for line in leaks:
            print(f"  - {line}")
    else:
        print("Vertraulichkeitsprüfung: Auftraggeber, Adressen und Unterlagen-Links kommen nicht vor.")
    print(f"Dateien: {OUT}")

    if open_browser and written:
        webbrowser.open(written[0].as_uri())
    return written


if __name__ == "__main__":
    write_preview(open_browser=False)
