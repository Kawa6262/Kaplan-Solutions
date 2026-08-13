"""Header für bessere Zustellbarkeit (Posteingang statt Spam)."""

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


def _domain() -> str:
    return public_site_url().replace("https://", "").replace("http://", "")


def deliverability_headers(recipient: str | None = None) -> dict[str, str]:
    """RFC 8058 + List-ID — nur für Outreach / Newsletter (nicht für Verträge)."""
    reply = os.getenv("REPLY_EMAIL", "kontakt@kaplan-solutions.de").strip()
    subject = urllib.parse.quote("Abmeldung Kaplan Solutions")
    mailto = f"<mailto:{reply}?subject={subject}>"
    web = f"<{unsubscribe_url(recipient)}>"
    domain = _domain()
    return {
        "List-Unsubscribe": f"{mailto}, {web}",
        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        "List-ID": f"<outreach.{domain}>",
        "List-Help": f"<mailto:{reply}?subject=Hilfe%20Abmeldung>",
        "Feedback-ID": f"outreach:{domain}",
        "X-Entity-Ref-ID": f"ks-outreach-{domain}",
    }


def transactional_headers(ref: str | None = None) -> dict[str, str]:
    """Minimale Header für 1:1-Verträge, Rechnungen, Bestätigungen — kein List-Unsubscribe."""
    domain = _domain()
    suffix = (ref or "doc")[:40].replace(" ", "-")
    return {
        "X-Entity-Ref-ID": f"ks-contract-{suffix}-{domain}",
        "X-Auto-Response-Suppress": "All",
    }
