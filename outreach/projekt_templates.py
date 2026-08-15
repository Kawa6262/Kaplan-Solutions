"""Projekt-Ausschreibung an ausführende Betriebe.

Unterschied zur Partner-Vorlage: Hier wird kein Netzwerk beworben, sondern ein
benannter Auftrag angeboten. Der Betrieb soll in den ersten zwei Zeilen sehen,
dass es um echte Arbeit in seiner Stadt geht und nicht um Werbung.

Der Auftraggeber bleibt ungenannt. Name, Straße und die Unterlagen gehen erst
nach unterzeichnetem Vermittlungsvertrag heraus.
"""

from __future__ import annotations

import hashlib

from outreach.email_layout import (
    TEXT,
    body_block,
    highlight_box,
    safe,
    text_footer,
    wrap_outreach_email,
)
from outreach.projekt import AKTUELL, Ausschreibung
from outreach.urls import projekt_form_url

# Welche Leistungen einen Betrieb betreffen. Ein Elektriker soll nicht über
# Spielplätze lesen, sondern über seinen eigenen Anteil.
_TRADE_FOCUS: dict[str, list[str]] = {
    "SHK Betrieb Heizung Sanitär": [
        "Komplette Badmodernisierung inklusive Sanitärinstallation",
        "Heizungsarbeiten und Austausch der Heizkörper",
    ],
    "Badsanierung Firma": [
        "Komplette Badmodernisierung in 14 Wohneinheiten",
        "Sanitärinstallation",
    ],
    "Elektroinstallateur Bau": [
        "Elektroarbeiten in 14 Wohneinheiten",
        "Schalterarbeiten und Neuinstallation",
    ],
    "Malerbetrieb": [
        "Malerarbeiten an Wänden und Decken in 14 Wohneinheiten",
        "Vorarbeiten nach Rückbau und Trockenbau",
    ],
    "Fliesenleger Betrieb": [
        "Fliesenarbeiten in Bädern und Wohnräumen",
        "14 Wohneinheiten in zwei Objekten",
    ],
    "Bodenleger Parkett": [
        "Bodenarbeiten in 14 Wohneinheiten",
        "Zwei Objekte, Vergabe im Paket möglich",
    ],
    "Estrichleger Firma": [
        "Estricharbeiten im Zuge der Bodensanierung",
        "14 Wohneinheiten in zwei Objekten",
    ],
    "Trockenbau Firma": [
        "Trockenbauarbeiten: neue Trennwände, Dämmung, Brandschutzwände",
        "Maurerarbeiten im Zuge des Umbaus",
    ],
    "Abbruch Rückbau Firma": [
        "Rückbau- und Abbrucharbeiten in zwei Objekten",
        "Vorlauf für die anschließende Modernisierung",
    ],
    "Fensterbau Montage": [
        "Fenster- und Türenarbeiten im Vorderhaus",
        "Innentüren im zweiten Objekt",
    ],
    "Tischlerei Innenausbau": [
        "Fenster-, Türen- und Innentürenarbeiten",
        "Innenausbau in 14 Wohneinheiten",
    ],
    "Maurerbetrieb": [
        "Maurer- und Trockenbauarbeiten, neue Trennwände",
        "Teilweiser Umbau inklusive Kellerumbau",
    ],
    "Brandschutz Fachbetrieb": [
        "Brandschutzwände und Brandschutzmaßnahmen",
        "Neunfamilienhaus mit Vorderhaus, Anbau und Hinterhaus",
    ],
    "Garten- und Landschaftsbau": [
        "Außenanlagen inklusive Spielplatz",
        "Arbeiten im Zuge der Gesamtmodernisierung",
    ],
}

_FULL_SCOPE_TRADES = {
    "Generalunternehmer Bau",
    "Bauunternehmen Sanierung",
    "Schlüsselfertigbau",
    "Komplettsanierung Wohnung",
    "Sanierungsbau Firma",
    "Innenausbau Firma",
}


def _variant(company: str) -> int:
    return int(hashlib.md5(company.encode()).hexdigest(), 16) % 3


def _euro(value: int) -> str:
    return f"{value:,}".replace(",", ".") + " €"


def build_subject(company: str, city: str, ausschreibung: Ausschreibung = AKTUELL) -> str:
    v = _variant(company)
    einheiten = ausschreibung.einheiten_gesamt
    if v == 0:
        return f"Bauvorhaben {ausschreibung.region} — ausführende Firma gesucht"
    if v == 1:
        return f"Anfrage: Modernisierung {einheiten} Wohneinheiten in {ausschreibung.region}"
    return f"Konkreter Auftrag in {ausschreibung.region} ({ausschreibung.referenz})"


def _focus_lines(trade: str, ausschreibung: Ausschreibung) -> tuple[str, list[str]]:
    """Einleitungssatz und Leistungsauszug passend zum Gewerk."""
    if trade in _FULL_SCOPE_TRADES or trade not in _TRADE_FOCUS:
        intro = (
            "Gesucht wird bevorzugt ein Betrieb, der die Modernisierung als "
            "Gesamtpaket übernimmt. Einzelne Gewerke sind ebenfalls möglich."
        )
        return intro, ausschreibung.alle_leistungen
    intro = (
        "Für Ihr Gewerk geht es konkret um diese Arbeiten. Wenn Sie darüber "
        "hinaus weitere Gewerke abdecken, schreiben Sie es gerne dazu."
    )
    return intro, _TRADE_FOCUS[trade]


def build_bodies(
    company: str,
    city: str,
    trade: str,
    recipient_email: str = "",
    prospect_id: int | None = None,
    ausschreibung: Ausschreibung = AKTUELL,
) -> tuple[str, str]:
    region = ausschreibung.region
    standort = city or region
    form_url = projekt_form_url(prospect_id)
    intro, leistungen = _focus_lines(trade, ausschreibung)
    volumen = _euro(ausschreibung.volumen_gesamt)
    einheiten = ausschreibung.einheiten_gesamt
    anfrage_hinweis = (
        f"Bitte vermerken Sie in der Beschreibung: „Projekt {region} / Vermittlung“ — "
        "so ordnen wir Ihre Anfrage dem Bauvorhaben zu."
    )

    leistungs_text = "\n".join(f"- {l}" for l in leistungen)
    hinweis_text = "\n".join(f"- {h}" for h in ausschreibung.hinweise)

    text = f"""Sehr geehrte Damen und Herren,

wir vermitteln derzeit ein konkretes Bauvorhaben in {region} und suchen dafür eine ausführende Firma in Ihrer Region. {company} in {standort} ist uns dabei als möglicher Partner aufgefallen.

Das Vorhaben umfasst die Modernisierung von zwei Mehrfamilienhäusern mit insgesamt {einheiten} Wohneinheiten. Das Gesamtvolumen liegt bei rund {volumen} brutto. Der Auftraggeber bleibt bis zur vertraglichen Einbindung vertraulich — Details und Unterlagen erhalten Sie erst nach einem persönlichen Abstimmungsgespräch.

{intro}

Leistungsumfang (Auszug):
{leistungs_text}

Rahmenbedingungen:
{hinweis_text}

Passt das zu Ihrer Kapazität und Ihrem Leistungsspektrum?
Stellen Sie bitte eine kurze Anfrage über unsere Website:

{form_url}

{anfrage_hinweis}

Kaplan Solutions vermittelt Bauleistungen zwischen Auftraggebern und ausführenden Betrieben. Für Sie entstehen keine Listengebühren und keine Kosten für die Anfrage. Eine Vergütung fällt ausschließlich im Erfolgsfall an, wenn der Bauvertrag zustande kommt.

Mit freundlichen Grüßen
Kaplan Solutions
{text_footer(recipient_email, "Geschäftliche Kontaktaufnahme gemäß § 7 Abs. 3 UWG (Bauleistungen).")}
"""

    leistungs_html = "".join(f"<li style='margin:0 0 6px 0;'>{safe(l)}</li>" for l in leistungen)
    hinweis_html = "".join(f"<li style='margin:0 0 6px 0;'>{safe(h)}</li>" for h in ausschreibung.hinweise)

    body_html = body_block(
        f'wir vermitteln derzeit ein konkretes Bauvorhaben in '
        f'<strong style="color:{TEXT};">{safe(region)}</strong> und suchen dafür eine '
        f'ausführende Firma in Ihrer Region. '
        f'<strong style="color:{TEXT};">{safe(company)}</strong> in {safe(standort)} '
        "ist uns dabei als möglicher Partner aufgefallen.",
        f"Das Vorhaben umfasst die Modernisierung von zwei Mehrfamilienhäusern mit "
        f"insgesamt {einheiten} Wohneinheiten. Der Auftraggeber bleibt bis zur "
        "vertraglichen Einbindung vertraulich — Details und Unterlagen erhalten Sie "
        "erst nach einem persönlichen Abstimmungsgespräch.",
        intro,
    ) + highlight_box(
        f'<span style="color:{TEXT};font-weight:600;">Gesamtvolumen rund {volumen} brutto</span>'
        f"<br>{einheiten} Wohneinheiten · {safe(region)} und Umgebung"
    ) + (
        f'<p style="margin:0 0 8px 0;color:{TEXT};font-size:15px;font-weight:600;">'
        f"Leistungsumfang (Auszug)</p>"
        f'<ul style="margin:0 0 20px 0;padding-left:20px;color:{TEXT};font-size:15px;line-height:1.6;">'
        f'{leistungs_html}</ul>'
        f'<p style="margin:0 0 8px 0;color:{TEXT};font-size:15px;font-weight:600;">Rahmenbedingungen</p>'
        f'<ul style="margin:0 0 18px 0;padding-left:20px;color:{TEXT};font-size:15px;line-height:1.6;">'
        f'{hinweis_html}</ul>'
    ) + body_block(
        "Passt das zu Ihrer Kapazität und Ihrem Leistungsspektrum? "
        "Stellen Sie bitte eine kurze Anfrage über unsere Website — "
        "wir melden uns zeitnah persönlich bei Ihnen.",
    ) + highlight_box(
        f'<strong style="color:{TEXT};">Bitte in der Beschreibung vermerken:</strong><br>'
        f'„Projekt {safe(region)} / Vermittlung“<br>'
        "<span style='font-size:14px;'>So ordnen wir Ihre Anfrage dem Bauvorhaben zu.</span>"
    ) + body_block(
        f'Für Sie entstehen <strong style="color:{TEXT};">keine Listengebühren</strong> und keine '
        "Kosten für die Anfrage. Eine Vergütung fällt ausschließlich im Erfolgsfall an, wenn der "
        "Bauvertrag zustande kommt.",
    )

    html = wrap_outreach_email(
        headline=f"Bauvorhaben {region} — {einheiten} Wohneinheiten",
        eyebrow="Konkrete Ausschreibung",
        body_html=body_html,
        cta_label="Anfrage auf kaplan-solutions.de",
        cta_url=form_url,
        recipient_email=recipient_email,
        legal="Geschäftliche Kontaktaufnahme gemäß § 7 Abs. 3 UWG (Bauleistungen).",
    )

    return text, html
