"""Header und URLs für bessere Zustellbarkeit (Posteingang statt Spam)."""

from __future__ import annotations

import os
import urllib.parse


def public_site_url() -> str:
    return (
        os.getenv("COMPANY_WEBSITE", "").strip().rstrip("/")
        or os.getenv("SITE_URL", "https://kaplan-solutions.de").strip().rstrip("/")
    )


def unsubscribe_url(email: str | None = None) -> str:
    base = f"{public_site_url()}/abmelden"
    if email:
        return f"{base}?email={urllib.parse.quote(email.strip())}"
    return base


def deliverability_headers(recipient: str | None = None) -> dict[str, str]:
    """RFC 8058-kompatible Abmelde-Header — Gmail bevorzugt https + mailto."""
    reply = os.getenv("REPLY_EMAIL", "kontakt@kaplan-solutions.de").strip()
    subject = urllib.parse.quote("Abmeldung Kaplan Solutions")
    mailto = f"<mailto:{reply}?subject={subject}>"
    web = f"<{unsubscribe_url(recipient)}>"
    return {
        "List-Unsubscribe": f"{mailto}, {web}",
        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
    }
