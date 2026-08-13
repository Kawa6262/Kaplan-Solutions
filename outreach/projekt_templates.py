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
    reply_hint_html,
    safe,
    text_footer,
    wrap_outreach_email,
)
from outreach.projekt import AKTUELL, Ausschreibung
from outreach.urls import partner_form_url

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
    form_url = partner_form_url(prospect_id)
    intro, leistungen = _focus_lines(trade, ausschreibung)
    volumen = _euro(ausschreibung.volumen_gesamt)
    einheiten = ausschreibung.einheiten_gesamt

    objekt_text = "\n\n".join(
        f"{o.bezeichnung} — {o.einheiten}, rund {_euro(o.volumen_brutto)} brutto\n{o.umfang}"
        for o in ausschreibung.objekte
    )
    leistungs_text = "\n".join(f"- {l}" for l in leistungen)
    hinweis_text = "\n".join(f"- {h}" for h in ausschreibung.hinweise)

    text = f"""Sehr geehrte Damen und Herren,

uns liegt ein konkretes Bauvorhaben in {region} vor, und wir suchen dafür eine ausführende Firma. Wir schreiben {company} an, weil Sie in {standort} tätig sind und das Objekt in Ihrem Einzugsgebiet liegt.

Zwei Mehrfamilienhäuser in {region}, zusammen {einheiten} Wohneinheiten, Gesamtvolumen rund {volumen} brutto.

{objekt_text}

{intro}

{leistungs_text}

Rahmenbedingungen:
{hinweis_text}

Passt das zu Ihrer Kapazität?
Antworten Sie einfach auf diese E-Mail mit Ihrem Gewerk und dem möglichen Ausführungszeitraum. Wir melden uns persönlich und stimmen einen Ortstermin ab.

Zur Einordnung: Kaplan Solutions vermittelt das Bauvorhaben. Für Sie entstehen keine Listengebühren und keine Kosten für die Anfrage. Eine Vergütung fällt ausschließlich im Erfolgsfall an, wenn der Bauvertrag zustande kommt.

Referenz: {ausschreibung.referenz}

Mit freundlichen Grüßen
Kaplan Solutions
{text_footer(recipient_email, "Geschäftliche Kontaktaufnahme gemäß § 7 Abs. 3 UWG (Bauleistungen).")}
"""

    objekt_html = "".join(
        f'<p style="margin:0 0 14px 0;">'
        f'<strong style="color:{TEXT};">{safe(o.bezeichnung)} — {safe(o.einheiten)}, '
        f'rund {_euro(o.volumen_brutto)} brutto</strong><br>{safe(o.umfang)}</p>'
        for o in ausschreibung.objekte
    )
    leistungs_html = "".join(f"<li style='margin:0 0 6px 0;'>{safe(l)}</li>" for l in leistungen)
    hinweis_html = "".join(f"<li style='margin:0 0 6px 0;'>{safe(h)}</li>" for h in ausschreibung.hinweise)

    body_html = body_block(
        f'uns liegt ein konkretes Bauvorhaben in <strong style="color:{TEXT};">{safe(region)}</strong> '
        f'vor, und wir suchen dafür eine ausführende Firma. Wir schreiben '
        f'<strong style="color:{TEXT};">{safe(company)}</strong> an, weil Sie in '
        f'{safe(standort)} tätig sind und das Objekt in Ihrem Einzugsgebiet liegt.',
    ) + highlight_box(
        f'Zwei Mehrfamilienhäuser, zusammen {einheiten} Wohneinheiten<br>'
        f'<span style="color:{TEXT};font-weight:600;">Gesamtvolumen rund {volumen} brutto</span>'
    ) + body_block(objekt_html, intro) + (
        f'<ul style="margin:0 0 20px 0;padding-left:20px;color:{TEXT};font-size:15px;line-height:1.6;">'
        f'{leistungs_html}</ul>'
        f'<p style="margin:0 0 8px 0;color:{TEXT};font-size:15px;font-weight:600;">Rahmenbedingungen</p>'
        f'<ul style="margin:0 0 18px 0;padding-left:20px;color:{TEXT};font-size:15px;line-height:1.6;">'
        f'{hinweis_html}</ul>'
    ) + body_block(
        f'Für Sie entstehen <strong style="color:{TEXT};">keine Listengebühren</strong> und keine '
        "Kosten für die Anfrage. Eine Vergütung fällt ausschließlich im Erfolgsfall an, wenn der "
        f"Bauvertrag zustande kommt. Referenz: {safe(ausschreibung.referenz)}",
    ) + reply_hint_html()

    html = wrap_outreach_email(
        headline=f"Bauvorhaben {region} — {einheiten} Wohneinheiten",
        eyebrow="Konkrete Ausschreibung",
        body_html=body_html,
        cta_label="Unterlagen anfordern",
        cta_url=form_url,
        recipient_email=recipient_email,
        legal="Geschäftliche Kontaktaufnahme gemäß § 7 Abs. 3 UWG (Bauleistungen).",
    )

    return text, html
