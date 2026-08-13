"""Die aktuell ausgeschriebenen Bauvorhaben.

Getrennt von der Vorlage, damit das nächste Projekt eine Datenänderung ist und
keine Codeänderung.

Wichtig: Auftraggeber, Straße und Hausnummer stehen hier bewusst NICHT in den
Feldern, die in die Mail wandern. Wer den Bauherrn kennt, kann uns umgehen, und
die Erfolgsprovision ist die einzige Einnahme aus der Vermittlung. Die genaue
Adresse und die Unterlagen bekommt ein Betrieb erst nach unterzeichnetem
Vermittlungsvertrag.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Objekt:
    bezeichnung: str
    lage: str
    einheiten: str
    umfang: str
    volumen_brutto: int
    leistungen: list[str]


@dataclass(frozen=True)
class Ausschreibung:
    referenz: str
    titel: str
    region: str
    objekte: list[Objekt]
    # Für Betriebe, die alles übernehmen können. Die Leistungen der einzelnen
    # Objekte einfach aneinanderzuhängen liest sich doppelt, weil beide Objekte
    # Bäder, Böden und Elektro enthalten.
    leistungen_gesamt: list[str] = field(default_factory=list)
    hinweise: list[str] = field(default_factory=list)
    aktiv: bool = True

    @property
    def volumen_gesamt(self) -> int:
        return sum(o.volumen_brutto for o in self.objekte)

    @property
    def einheiten_gesamt(self) -> int:
        return sum(int(o.einheiten.split()[0]) for o in self.objekte)

    @property
    def alle_leistungen(self) -> list[str]:
        if self.leistungen_gesamt:
            return self.leistungen_gesamt
        seen: list[str] = []
        for objekt in self.objekte:
            for leistung in objekt.leistungen:
                if leistung not in seen:
                    seen.append(leistung)
        return seen


AKTUELL = Ausschreibung(
    referenz="KS-2026-DU-01",
    titel="Modernisierung von zwei Mehrfamilienhäusern",
    region="Duisburg",
    objekte=[
        Objekt(
            bezeichnung="Objekt 1",
            lage="Duisburg, Stadtteil zentrumsnah",
            einheiten="9 Wohneinheiten",
            umfang=(
                "Vorderhaus vom Erdgeschoss bis zum Dachgeschoss, Anbau mit Erd- und "
                "Untergeschoss sowie Hinterhaus als Loft-Einheit über mehrere Ebenen "
                "inklusive Garage. Umfassende Modernisierung mit teilweisem Umbau."
            ),
            volumen_brutto=475_000,
            leistungen=[
                "Rückbau- und Abbrucharbeiten",
                "Maurer- und Trockenbauarbeiten (Trennwände, Dämmung, Brandschutzwände)",
                "Boden-, Fliesen- und Malerarbeiten",
                "Komplette Badmodernisierung inklusive Sanitärinstallation",
                "Heizungs- und Elektroarbeiten",
                "Fenster- und Türenarbeiten",
                "Brandschutzmaßnahmen",
                "Außenanlagen inklusive Kellerumbau und Spielplatz",
            ],
        ),
        Objekt(
            bezeichnung="Objekt 2",
            lage="Duisburg, Stadtteil zentrumsnah",
            einheiten="5 Wohneinheiten",
            umfang=(
                "Souterrain (nur Heizungsanschluss), Erdgeschoss, erstes und zweites "
                "Obergeschoss sowie Dachgeschoss. Modernisierung der einzelnen Wohnungen."
            ),
            volumen_brutto=160_000,
            leistungen=[
                "Rückbau- und Abbrucharbeiten",
                "Boden- und Malerarbeiten an Wänden und Decken",
                "Komplette Badmodernisierung inklusive Sanitärinstallation",
                "Austausch der Heizkörper",
                "Elektro- und Schalterarbeiten",
                "Innentüren",
            ],
        ),
    ],
    leistungen_gesamt=[
        "Rückbau- und Abbrucharbeiten in beiden Objekten",
        "Maurer- und Trockenbauarbeiten: Trennwände, Dämmung, Brandschutzwände",
        "Boden-, Fliesen- und Malerarbeiten in allen Einheiten",
        "Komplette Badmodernisierung inklusive Sanitärinstallation",
        "Heizungsarbeiten, in einem Objekt Austausch der Heizkörper",
        "Elektro- und Schalterarbeiten",
        "Fenster-, Außen- und Innentüren",
        "Brandschutzmaßnahmen",
        "Außenanlagen inklusive Kellerumbau und Spielplatz",
    ],
    hinweise=[
        "Funktionale Leistungsverzeichnisse je Wohneinheit liegen vor, dazu Visualisierungen und Pläne.",
        "Das Aufmaß ist vor Ort eigenverantwortlich zu erstellen, ein Ortstermin ist möglich.",
        "Vergabe bevorzugt als Gesamtpaket, einzelne Gewerke sind ebenfalls möglich.",
    ],
)
