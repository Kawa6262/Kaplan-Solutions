"""Zentrale Firmendaten für Impressum, Datenschutz und AGB."""

import os

# legal_form: privat | einzelunternehmen | gmbh
#   privat            = natürliche Person, noch keine Firma (Projekt/Marke)
#   einzelunternehmen = eingetragener Einzelunternehmer / Freiberufler
#   gmbh              = eingetragene Gesellschaft (GmbH/UG)


def _build_company() -> dict:
    legal_form = os.getenv("COMPANY_LEGAL_FORM", "privat").strip().lower()
    brand = os.getenv("COMPANY_BRAND", "Kaplan Solutions").strip()
    operator = os.getenv("COMPANY_OPERATOR", "").strip()
    street = os.getenv("COMPANY_STREET", "").strip()
    zip_code = os.getenv("COMPANY_ZIP", "").strip()
    city = os.getenv("COMPANY_CITY", "Berlin").strip()
    zip_city = f"{zip_code} {city}".strip() if zip_code else city

    is_incorporated = legal_form == "gmbh"
    is_einzel = legal_form == "einzelunternehmen"

    if is_incorporated:
        legal_name = os.getenv("COMPANY_NAME", f"{brand} GmbH").strip()
        director = os.getenv("COMPANY_DIRECTOR", operator).strip()
    elif is_einzel:
        legal_name = f"{operator or '[Name in .env: COMPANY_OPERATOR]'} · {brand}"
        director = operator
    else:
        # Noch keine Firma — natürliche Person hinter der Marke
        legal_name = operator or "[Name in .env: COMPANY_OPERATOR]"
        director = operator

    if not operator:
        operator = "[Name in .env: COMPANY_OPERATOR]"

    register_number = os.getenv("COMPANY_REGISTER_NUMBER", "").strip()
    register_court = os.getenv("COMPANY_REGISTER_COURT", "Amtsgericht Berlin-Charlottenburg").strip()

    c = {
        "brand": brand,
        "legal_form": legal_form,
        "is_incorporated": is_incorporated,
        "is_einzel": is_einzel,
        "is_privat": legal_form == "privat",
        "operator_name": operator,
        "legal_name": legal_name,
        "street": street or "[Straße und Hausnummer in .env: COMPANY_STREET]",
        "zip_city": zip_city,
        "country": os.getenv("COMPANY_COUNTRY", "Deutschland"),
        "email": os.getenv("REPLY_EMAIL", "kontakt@kaplan-solutions.de").strip(),
        "phone": os.getenv("COMPANY_PHONE", "+49 (0)30 123 456 789").strip(),
        "website": os.getenv("COMPANY_WEBSITE", "https://kaplan-solutions.de").strip(),
        "director": director,
        "register_court": register_court,
        "register_number": register_number,
        "vat_id": os.getenv("COMPANY_VAT_ID", "").strip(),
        "content_responsible": os.getenv("COMPANY_CONTENT_RESPONSIBLE", "").strip() or operator,
        "region_label": os.getenv("COMPANY_REGION", "Berlin & DACH"),
    }

    c["has_register"] = is_incorporated and bool(register_number)
    c["address_complete"] = bool(street) and not c["street"].startswith("[")
    return c


COMPANY = _build_company()


def company_footer_text() -> str:
    """Signatur für E-Mails (Text)."""
    c = COMPANY
    lines = [c["brand"]]
    if c["is_incorporated"]:
        lines = [c["legal_name"], f"{c['street']} · {c['zip_city']}"]
    elif c["is_einzel"]:
        lines.append(c["operator_name"])
        if c["address_complete"]:
            lines.append(f"{c['street']} · {c['zip_city']}")
        else:
            lines.append(c["zip_city"])
    else:
        if c["operator_name"] and not c["operator_name"].startswith("["):
            lines.append(c["operator_name"])
        lines.append(c["zip_city"])
    return "\n".join(lines)
