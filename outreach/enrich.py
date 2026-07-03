"""E-Mail-Adressen von Firmenwebsites extrahieren."""

from __future__ import annotations

import re
import ssl
import urllib.parse
import urllib.request

from outreach.config import PREFERRED_EMAIL_PREFIXES, SKIP_EMAIL_DOMAINS
from outreach import storage

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

CONTACT_PATHS = (
    "",
    "/kontakt",
    "/contact",
    "/impressum",
    "/imprint",
    "/ueber-uns",
    "/about",
)


def _fetch(url: str) -> str:
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,*/*",
                "Accept-Language": "de-DE,de;q=0.9",
            },
        )
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=12, context=ctx) as resp:
            return resp.read(180000).decode("utf-8", errors="replace")
    except Exception:
        return ""


def _normalize_site(website: str) -> str:
    site = website.strip()
    if not site:
        return ""
    if not site.startswith(("http://", "https://")):
        site = "https://" + site
    return site.rstrip("/")


def _score_email(email: str, site_domain: str) -> int:
    email = email.lower().strip()
    local, _, domain = email.partition("@")
    if not domain or domain in SKIP_EMAIL_DOMAINS:
        return -999
    if any(x in email for x in ("noreply", "no-reply", "datenschutz", "privacy", "abuse")):
        return -100
    score = 0
    if site_domain and (domain == site_domain or domain.endswith("." + site_domain)):
        score += 30
    for i, prefix in enumerate(PREFERRED_EMAIL_PREFIXES):
        if local.startswith(prefix):
            score += 50 - i
            break
    if local in PREFERRED_EMAIL_PREFIXES:
        score += 20
    # Freemail weniger ideal für B2B, aber manchmal einzige Option
    freemail = {"gmail.com", "gmx.de", "web.de", "t-online.de", "outlook.de", "icloud.com"}
    if domain in freemail:
        score -= 15
    return score


def extract_best_email(website: str) -> str | None:
    base = _normalize_site(website)
    if not base:
        return None
    parsed = urllib.parse.urlparse(base)
    site_domain = (parsed.hostname or "").lower()
    if site_domain.startswith("www."):
        site_domain = site_domain[4:]

    found: dict[str, int] = {}
    for path in CONTACT_PATHS:
        url = base if not path else base + path
        html = _fetch(url)
        if not html:
            continue
        for raw in EMAIL_RE.findall(html):
            email = raw.lower().strip().rstrip(".")
            if email.endswith(".png") or email.endswith(".jpg"):
                continue
            score = _score_email(email, site_domain)
            if score > -50:
                found[email] = max(found.get(email, -999), score)

    if not found:
        return None
    best = max(found.items(), key=lambda x: x[1])
    return best[0] if best[1] > 0 else None


def enrich_batch(limit: int) -> int:
    """Returns Anzahl erfolgreich angereicherter Prospects."""
    from outreach import pacing

    if not pacing.enrich_allowed():
        return 0
    rows = storage.prospects_to_enrich(limit)
    enriched = 0
    for row in rows:
        email = extract_best_email(row["website"] or "")
        if email and storage.is_unsubscribed(email):
            storage.mark_enriched(row["id"], email, "unsubscribed")
            continue
        if email:
            storage.mark_enriched(row["id"], email, "queued")
            enriched += 1
            campaign = row["campaign"] if "campaign" in row.keys() else "partner"
            storage.bump_counter("enriched", campaign=campaign or "partner")
        else:
            storage.mark_enriched(row["id"], None, "skipped")
    if enriched:
        print(f"[outreach] {enriched} E-Mail-Adressen gefunden", flush=True)
    return enriched
