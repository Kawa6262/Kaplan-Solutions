"""Gewerk → Branche (wie server._categorize_branche)."""

from __future__ import annotations


def categorize(text: str) -> str:
    raw = (text or "").strip().lower()
    if not raw or raw == "—":
        return "Sonstiges"
    rules = [
        ("Neubau", ("neubau", "mehrfamilien", "einfamilienhaus", "neugestaltung", "hausbaum")),
        ("Sanierung", ("sanierung", "renovierung", "modernisierung", "kernsanierung")),
        ("Rohbau", ("rohbau", "schalung", "betonbau", "bauunternehmen")),
        ("Ausbau", ("ausbau", "innenausbau", "trockenbau")),
        ("Tiefbau", ("tiefbau", "erdarbeiten", "straßenbau", "strassenbau")),
        ("Gewerbebau", ("gewerbe", "industrie", "halle", "logistik")),
        ("Wohnungsbau", ("wohnung", "wohnungsbau", "mfh", "efh")),
        ("Elektro", ("elektro", "elektrik", "photovoltaik")),
        ("SHK", ("shk", "sanitär", "heizung", "klima", "installateur")),
        ("Maler", ("maler",)),
        ("Dach", ("dachdecker", "dach")),
        ("Garten", ("garten", "landschaftsbau")),
    ]
    for label, keys in rules:
        if any(k.strip() in raw for k in keys):
            return label
    return raw[:48].title()
