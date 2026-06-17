"""Intensive Seriositäts-/Background-Prüfung von Firmen mit Quellenangaben.

Läuft im Hintergrund (Thread) nach jeder Anfrage und schreibt das Ergebnis
zurück ins Google Sheet (action=seriosity_update).

Datenquellen (je nach verfügbaren API-Keys):
  - Firmenwebsite + Impressum  (immer, kostenlos): Rechtsform, HRB, USt-IdNr,
    Adresse, Geschäftsführer, Kontaktdaten
  - RDAP (immer, kostenlos): Domain-Alter
  - Google Places API (GOOGLE_PLACES_API_KEY): Sterne-Bewertung + Anzahl
  - Serper.dev (SERPER_API_KEY): Web-Reputation, negative Signale, Treffer

Jede gefundene Info wird mit Quelle (URL) gespeichert, damit alles
nachprüfbar ist.
"""

from __future__ import annotations

import json
import os
import re
import ssl
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

FREE_EMAIL_DOMAINS = {
    "gmail.com", "googlemail.com", "yahoo.com", "yahoo.de", "hotmail.com",
    "hotmail.de", "outlook.com", "outlook.de", "live.de", "live.com",
    "icloud.com", "gmx.de", "gmx.net", "web.de", "t-online.de", "mail.de",
    "freenet.de", "aol.com", "proton.me", "protonmail.com",
}

LEGAL_FORMS = [
    ("GmbH & Co. KG", r"gmbh\s*&\s*co\.?\s*kg"),
    ("UG (haftungsbeschränkt)", r"ug\s*\(haftungsbeschr[aä]nkt\)|unternehmergesellschaft"),
    ("gGmbH", r"\bggmbh\b"),
    ("GmbH", r"\bgmbh\b"),
    ("AG", r"\baktiengesellschaft\b|\bag\b"),
    ("e.K.", r"\be\.?\s?k\.?\b|eingetragene[r]? kaufmann|kauffrau"),
    ("OHG", r"\bohg\b|offene handelsgesellschaft"),
    ("KG", r"\bkg\b|kommanditgesellschaft"),
    ("GbR", r"\bgbr\b|gesellschaft b[uü]rgerlichen rechts"),
    ("e.V.", r"\be\.?\s?v\.?\b|eingetragener verein"),
]

NEGATIVE_SIGNALS = [
    "insolvenz", "insolvent", "betrug", "betrüger", "abzocke", "abzocker",
    "abmahnung", "gesperrt", "fake", "unseriös", "warnung", "scam",
    "verurteilt", "klage", "pleite", "liquidation", "schwarze liste",
]
POSITIVE_SIGNALS = [
    "ausgezeichnet", "testsieger", "zertifiziert", "meisterbetrieb",
    "auszeichnung", "preisträger", "innung", "tüv", "iso 9001",
]


# ─────────────────────────────────────────────────────────────────────────────
# Einstieg
# ─────────────────────────────────────────────────────────────────────────────

def schedule_trust_check(payload: dict) -> None:
    """Startet die Prüfung im Hintergrund (blockiert die Antwort nicht)."""
    if not payload.get("ref"):
        return
    if not os.getenv("SHEETS_WEBHOOK_URL", "").strip():
        return
    thread = threading.Thread(target=_run_check, args=(payload.copy(),), daemon=True)
    thread.start()


def _run_check(payload: dict) -> None:
    try:
        result = run_trust_check(payload)
        _push_to_sheet(payload, result)
        print(
            f"[trust] {payload.get('ref')} → {result['score']}% "
            f"({result['status']}) quellen={len(result.get('quellen', []))}",
            flush=True,
        )
    except Exception as exc:
        print(f"[trust] Fehler für {payload.get('ref')}: {exc}", flush=True)


# ─────────────────────────────────────────────────────────────────────────────
# Hauptlogik
# ─────────────────────────────────────────────────────────────────────────────

def run_trust_check(payload: dict) -> dict:
    name = (payload.get("name") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    phone = (payload.get("phone") or "").strip()
    company = (payload.get("company_name") or payload.get("company") or "").strip()
    if company in ("—", "-"):
        company = ""
    role = payload.get("role") or ""
    message = (payload.get("message") or "").strip()
    if role == "bauherr":
        city = (payload.get("location") or "").split(",")[0].strip()
    else:
        city = (payload.get("region") or "").split(",")[0].strip()
    domain = _email_domain(email)

    checks: list[dict] = []
    sources: list[dict] = []
    fields: dict = {
        "rechtsform": "", "handelsregister": "", "ust_id": "",
        "adresse": "", "geschaeftsfuehrer": "", "domain_alter": "",
        "google_rating": "", "website": "",
    }
    positives: list[str] = []
    negatives: list[str] = []
    score = 50  # neutrale Basis

    def add(ok: bool, label: str, pts: int) -> None:
        checks.append({"ok": ok, "label": label, "pts": pts})

    def src(label: str, url: str) -> None:
        if url and not any(s["url"] == url for s in sources):
            sources.append({"label": label, "url": url})

    # — Kontakt-Qualität —
    if company:
        add(True, f"Firmenname angegeben: {company}", 6)
        score += 6
    elif role == "unternehmen":
        add(False, "Kein Firmenname angegeben (Auftragnehmer)", -10)
        score -= 10

    if domain and domain not in FREE_EMAIL_DOMAINS:
        add(True, f"Geschäftliche E-Mail-Domain (@{domain})", 10)
        score += 10
    elif domain in FREE_EMAIL_DOMAINS:
        add(False, f"Private E-Mail-Adresse (@{domain})", -6)
        score -= 6

    if _valid_de_phone(phone):
        add(True, "Telefonnummer plausibel (DE-Format)", 6)
        score += 6
    else:
        add(False, "Telefonnummer unvollständig/ungewöhnlich", -4)
        score -= 4

    if len(message) >= 40:
        add(True, "Ausführliche, konkrete Anfrage", 4)
        score += 4
    elif len(message) < 12:
        add(False, "Sehr kurze Anfrage (Spam-Risiko)", -6)
        score -= 6

    # — Website & Impressum (Tiefenprüfung) —
    website = _discover_website(domain, company)
    if website:
        fields["website"] = website
        src("Firmen-Website", website)
        w_pts, w_fields, w_sources, w_pos = _deep_website_check(website)
        score += w_pts
        for k, v in w_fields.items():
            if v and not fields.get(k):
                fields[k] = v
        for s in w_sources:
            src(s["label"], s["url"])
        positives.extend(w_pos)
        if w_fields.get("rechtsform"):
            add(True, f"Rechtsform erkannt: {w_fields['rechtsform']}", 8)
        if w_fields.get("handelsregister"):
            add(True, f"Handelsregister: {w_fields['handelsregister']}", 14)
        if w_fields.get("ust_id"):
            add(True, f"USt-IdNr vorhanden: {w_fields['ust_id']}", 5)
        if w_fields.get("geschaeftsfuehrer"):
            add(True, f"Geschäftsführung im Impressum: {w_fields['geschaeftsfuehrer']}", 4)
    else:
        add(False, "Keine erreichbare Firmen-Website gefunden", -5)
        score -= 5

    # — Domain-Alter (RDAP) —
    if domain and domain not in FREE_EMAIL_DOMAINS:
        years, reg_url = _domain_age_years(domain)
        if years is not None:
            label = f"{years} Jahr(e)" + (f" (registriert {datetime.now().year - years})" if years else "")
            fields["domain_alter"] = label
            if reg_url:
                src("Domain-Registrierung (RDAP)", reg_url)
            if years >= 5:
                add(True, f"Etablierte Domain: {label}", 12)
                score += 12
            elif years >= 2:
                add(True, f"Domain seit {label}", 8)
                score += 8
            else:
                add(False, f"Sehr junge Domain: {label}", 2)
                score += 2

    # — Google-Bewertungen (Places API) —
    rating, rating_count, places_url = _google_places(company or name, city)
    if rating is not None:
        stars = f"{rating:.1f} ★".replace(".", ",")
        fields["google_rating"] = f"{stars} ({rating_count} Bewertungen)"
        if places_url:
            src("Google Maps / Bewertungen", places_url)
        if rating >= 4.5 and rating_count >= 10:
            add(True, f"Hervorragende Bewertungen: {fields['google_rating']}", 22)
            score += 22
        elif rating >= 4.0:
            add(True, f"Gute Bewertungen: {fields['google_rating']}", 16)
            score += 16
        elif rating >= 3.0:
            add(False, f"Durchwachsene Bewertungen: {fields['google_rating']}", 4)
            score += 4
        else:
            add(False, f"Schlechte Bewertungen: {fields['google_rating']}", -12)
            score -= 12
        if rating_count >= 50:
            add(True, f"Viele Bewertungen ({rating_count}) — hohe Aussagekraft", 5)
            score += 5

    # — Web-Reputation (Serper) —
    rep_pts, rep_checks, rep_sources, rep_pos, rep_neg = _web_reputation(
        company or name, city
    )
    score += rep_pts
    checks.extend(rep_checks)
    for s in rep_sources:
        src(s["label"], s["url"])
    positives.extend(rep_pos)
    negatives.extend(rep_neg)

    # — Score finalisieren —
    score = max(0, min(100, score))
    if score >= 80:
        status, flags = "Sehr seriös", "🟢"
    elif score >= 60:
        status, flags = "Seriös", "🟢"
    elif score >= 40:
        status, flags = "Teilweise geprüft", "🟡"
    else:
        status, flags = "Wenig Vertrauen", "🔴"

    # Konfidenz: wie viele unabhängige Quellen?
    confidence = "Hoch" if len(sources) >= 3 else ("Mittel" if len(sources) >= 1 else "Niedrig")

    details = _build_details_text(
        score, status, fields, checks, positives, negatives, sources, confidence
    )

    return {
        "score": score,
        "status": status,
        "flags": flags,
        "confidence": confidence,
        "rechtsform": fields["rechtsform"],
        "handelsregister": fields["handelsregister"],
        "ust_id": fields["ust_id"],
        "adresse": fields["adresse"],
        "geschaeftsfuehrer": fields["geschaeftsfuehrer"],
        "domain_alter": fields["domain_alter"],
        "google_rating": fields["google_rating"],
        "website": fields["website"],
        "positive": positives,
        "negative": negatives,
        "quellen": sources,
        "checks": checks,
        "details": details,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Website-Tiefenprüfung
# ─────────────────────────────────────────────────────────────────────────────

def _discover_website(domain: str, company: str) -> str:
    """Findet die Firmen-Website (aus E-Mail-Domain oder via Suche)."""
    if domain and domain not in FREE_EMAIL_DOMAINS:
        for url in (f"https://{domain}", f"https://www.{domain}"):
            if _fetch_url(url):
                return url
    # Fallback: über Serper die offizielle Website suchen
    if company:
        site = _serper_find_website(company)
        if site:
            return site
    return ""


def _deep_website_check(website: str) -> tuple[int, dict, list, list]:
    """Crawlt Startseite + Impressum/Kontakt und extrahiert Firmendaten."""
    points = 0
    fields = {
        "rechtsform": "", "handelsregister": "", "ust_id": "",
        "adresse": "", "geschaeftsfuehrer": "",
    }
    sources: list[dict] = []
    positives: list[str] = []

    base = website.rstrip("/")
    home = _fetch_url(base)
    if home:
        points += 8  # erreichbar + HTTPS
        low = home.lower()
        for kw in POSITIVE_SIGNALS:
            if kw in low:
                positives.append(f"Website nennt: „{kw}“")

    # Impressum / Kontakt finden
    impressum_url = _find_subpage(base, home, ["impressum", "imprint", "kontakt", "legal"])
    imp_html = _fetch_url(impressum_url) if impressum_url else ""
    text_pool = (home or "") + "\n" + (imp_html or "")

    if impressum_url and imp_html:
        points += 10
        sources.append({"label": "Impressum", "url": impressum_url})

    # Rechtsform
    low_pool = text_pool.lower()
    for label, pat in LEGAL_FORMS:
        if re.search(pat, low_pool):
            fields["rechtsform"] = label
            break

    # Handelsregister
    m = re.search(r"\b(HR[AB]\s?\d{1,6}\s?[A-Z]?)\b", text_pool)
    if m:
        fields["handelsregister"] = m.group(1).replace("  ", " ").strip()

    # USt-IdNr
    m = re.search(r"\bDE\s?\d{9}\b", text_pool)
    if m:
        fields["ust_id"] = m.group(0).replace(" ", "")

    # Geschäftsführer
    m = re.search(
        r"(?:gesch[aä]ftsf[uü]hrer(?:in)?|inhaber(?:in)?|vertreten durch)[:\s]+"
        r"([A-ZÄÖÜ][\wäöüß.\-]+(?:\s+[A-ZÄÖÜ][\wäöüß.\-]+){1,3})",
        text_pool,
    )
    if m:
        fields["geschaeftsfuehrer"] = m.group(1).strip()

    # Adresse (Straße + PLZ Ort)
    m = re.search(
        r"([A-ZÄÖÜ][\wäöüß.\-]+(?:str(?:aße|\.)|weg|allee|platz|ring|gasse)\s?\d+[a-z]?)[\s,]*"
        r"(\d{5})\s+([A-ZÄÖÜ][\wäöüß.\- ]+)",
        text_pool,
        re.IGNORECASE,
    )
    if m:
        fields["adresse"] = f"{m.group(1)}, {m.group(2)} {m.group(3)}".strip()

    return points, fields, sources, positives


def _find_subpage(base: str, home_html: str, keywords: list[str]) -> str:
    """Sucht Link zu Impressum/Kontakt in der Startseite, sonst rät Standardpfade."""
    if home_html:
        for m in re.finditer(r'href=["\']([^"\']+)["\']', home_html, re.IGNORECASE):
            href = m.group(1)
            low = href.lower()
            if any(kw in low for kw in keywords):
                return urllib.parse.urljoin(base + "/", href)
    for kw in ("impressum", "kontakt", "imprint"):
        guess = f"{base}/{kw}"
        if _fetch_url(guess):
            return guess
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# Domain-Alter via RDAP (kostenlos)
# ─────────────────────────────────────────────────────────────────────────────

def _domain_age_years(domain: str) -> tuple[int | None, str]:
    url = f"https://rdap.org/domain/{urllib.parse.quote(domain)}"
    raw = _fetch_url(url, timeout=8)
    if not raw:
        return None, ""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None, ""
    for event in data.get("events", []) or []:
        if event.get("eventAction") in ("registration", "registered"):
            date_str = event.get("eventDate", "")
            try:
                reg = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                years = int((datetime.now(timezone.utc) - reg).days / 365.25)
                return years, url
            except ValueError:
                continue
    return None, ""


# ─────────────────────────────────────────────────────────────────────────────
# Google Places (Bewertungen)
# ─────────────────────────────────────────────────────────────────────────────

def _google_places(company: str, city: str) -> tuple[float | None, int, str]:
    key = os.getenv("GOOGLE_PLACES_API_KEY", "").strip()
    if not key or not company:
        return None, 0, ""
    query = f"{company} {city}".strip()
    try:
        find_url = (
            "https://maps.googleapis.com/maps/api/place/findplacefromtext/json?"
            + urllib.parse.urlencode({
                "input": query,
                "inputtype": "textquery",
                "fields": "place_id,name",
                "language": "de",
                "key": key,
            })
        )
        data = json.loads(_fetch_url(find_url, timeout=10) or "{}")
        cands = data.get("candidates") or []
        if not cands:
            return None, 0, ""
        place_id = cands[0].get("place_id")
        if not place_id:
            return None, 0, ""
        det_url = (
            "https://maps.googleapis.com/maps/api/place/details/json?"
            + urllib.parse.urlencode({
                "place_id": place_id,
                "fields": "rating,user_ratings_total,url",
                "language": "de",
                "key": key,
            })
        )
        det = json.loads(_fetch_url(det_url, timeout=10) or "{}")
        result = det.get("result") or {}
        rating = result.get("rating")
        count = result.get("user_ratings_total", 0)
        maps_url = result.get("url", "")
        if rating is not None:
            return float(rating), int(count), maps_url
    except Exception as exc:
        print(f"[trust] Places-Fehler: {exc}", flush=True)
    return None, 0, ""


# ─────────────────────────────────────────────────────────────────────────────
# Web-Reputation via Serper (Google-Suche)
# ─────────────────────────────────────────────────────────────────────────────

def _serper_post(query: str) -> dict:
    key = os.getenv("SERPER_API_KEY", "").strip()
    if not key:
        return {}
    try:
        body = json.dumps({"q": query, "gl": "de", "hl": "de", "num": 8}).encode()
        req = urllib.request.Request(
            "https://google.serper.dev/search",
            data=body,
            headers={"X-API-KEY": key, "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        print(f"[trust] Serper-Fehler: {exc}", flush=True)
        return {}


def _serper_find_website(company: str) -> str:
    data = _serper_post(f"{company} offizielle Website")
    for item in (data.get("organic") or [])[:3]:
        link = item.get("link", "")
        low = link.lower()
        if not any(p in low for p in ("facebook", "instagram", "linkedin",
                                       "xing", "wikipedia", "youtube",
                                       "11880", "gelbeseiten", "yelp")):
            return link
    return ""


def _web_reputation(company: str, city: str) -> tuple[int, list, list, list, list]:
    points = 0
    checks: list[dict] = []
    sources: list[dict] = []
    positives: list[str] = []
    negatives: list[str] = []
    if not company:
        return 0, checks, sources, positives, negatives

    data = _serper_post(f"{company} {city} Bewertung Erfahrungen")
    organic = data.get("organic") or []
    if organic:
        points += 8
        checks.append({"ok": True, "label": f"{len(organic)} Web-Treffer gefunden", "pts": 8})
        for item in organic[:3]:
            if item.get("link"):
                sources.append({"label": item.get("title", "Web-Treffer")[:50],
                                "url": item["link"]})
    else:
        checks.append({"ok": False, "label": "Keine Web-Treffer gefunden", "pts": -8})
        points -= 8

    # Bewertungs-Plattformen in Treffern?
    blob = json.dumps(data).lower()
    for platf in ("provenexpert", "trustpilot", "google", "gelbeseiten", "11880"):
        if platf in blob:
            positives.append(f"Präsenz auf Bewertungsplattform: {platf}")
            break

    # Negative / positive Signale
    found_neg = [s for s in NEGATIVE_SIGNALS if s in blob]
    if found_neg:
        negatives.append("Warnsignale in Suche: " + ", ".join(sorted(set(found_neg))[:5]))
        points -= 30
        checks.append({"ok": False, "label": "⚠️ Negative Signale gefunden", "pts": -30})
    found_pos = [s for s in POSITIVE_SIGNALS if s in blob]
    if found_pos:
        positives.append("Positive Signale: " + ", ".join(sorted(set(found_pos))[:5]))
        points += 8
        checks.append({"ok": True, "label": "Positive Reputationssignale", "pts": 8})

    return points, checks, sources, positives, negatives


# ─────────────────────────────────────────────────────────────────────────────
# Report-Text
# ─────────────────────────────────────────────────────────────────────────────

def _build_details_text(score, status, fields, checks, positives, negatives,
                        sources, confidence) -> str:
    lines = [
        f"SERIOSITÄTS-SCORE: {score}% — {status}",
        f"Konfidenz der Prüfung: {confidence} ({len(sources)} Quelle(n))",
        "",
        "FIRMENDATEN:",
        f"  Rechtsform:       {fields.get('rechtsform') or '— nicht gefunden'}",
        f"  Handelsregister:  {fields.get('handelsregister') or '— nicht gefunden'}",
        f"  USt-IdNr:         {fields.get('ust_id') or '— nicht gefunden'}",
        f"  Adresse:          {fields.get('adresse') or '— nicht gefunden'}",
        f"  Geschäftsführung: {fields.get('geschaeftsfuehrer') or '— nicht gefunden'}",
        f"  Firmenalter:      {fields.get('domain_alter') or '— unbekannt'}",
        f"  Google-Bewertung: {fields.get('google_rating') or '— keine gefunden'}",
        f"  Website:          {fields.get('website') or '— keine gefunden'}",
        "",
        "EINZELPRÜFUNGEN:",
    ]
    for c in checks:
        icon = "✅" if c["ok"] else "⚠️"
        lines.append(f"  {icon} {c['label']} ({c.get('pts', 0):+d})")

    if positives:
        lines += ["", "POSITIV:"]
        lines += [f"  + {p}" for p in positives]
    if negatives:
        lines += ["", "⚠️ ACHTUNG:"]
        lines += [f"  - {n}" for n in negatives]

    lines += ["", "QUELLEN (selbst nachprüfen):"]
    if sources:
        for s in sources:
            lines.append(f"  • {s['label']}: {s['url']}")
    else:
        lines.append("  — keine externen Quellen gefunden")

    lines += [
        "",
        "Hinweis: Automatische Recherche. Bei wichtigen Entscheidungen bitte "
        "die Quellen prüfen und ggf. Nachweise (HR-Auszug, Referenzen) anfordern.",
    ]
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Ergebnis ans Sheet senden
# ─────────────────────────────────────────────────────────────────────────────

def _push_to_sheet(payload: dict, result: dict) -> None:
    url = os.getenv("SHEETS_WEBHOOK_URL", "").strip()
    if not url:
        return

    is_bau = payload.get("role") == "bauherr"
    company = payload.get("company", "")
    if not is_bau:
        company = payload.get("company_name") or company

    body = json.dumps({
        "action": "seriosity_update",
        "ref": payload.get("ref"),
        "name": payload.get("name", ""),
        "firma": company,
        "rolle": "Auftraggeber" if is_bau else "Auftragnehmer",
        "score": result["score"],
        "status": result["status"],
        "flags": result["flags"],
        "confidence": result.get("confidence", ""),
        "rechtsform": result.get("rechtsform", ""),
        "handelsregister": result.get("handelsregister", ""),
        "ust_id": result.get("ust_id", ""),
        "adresse": result.get("adresse", ""),
        "geschaeftsfuehrer": result.get("geschaeftsfuehrer", ""),
        "domain_alter": result.get("domain_alter", ""),
        "google_rating": result.get("google_rating", ""),
        "website": result.get("website", ""),
        "quellen": result.get("quellen", []),
        "positive": result.get("positive", []),
        "negative": result.get("negative", []),
        "details": result["details"],
    }).encode("utf-8")

    headers = {"Content-Type": "application/json", "User-Agent": USER_AGENT}

    def post(target: str) -> None:
        req = urllib.request.Request(target, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            if '"ok":false' in raw.replace(" ", ""):
                raise RuntimeError(raw[:300])

    try:
        post(url)
    except urllib.error.HTTPError as exc:
        if exc.code in (301, 302, 303, 307, 308):
            loc = exc.headers.get("Location")
            if loc:
                post(loc)
                return
        raise


# ─────────────────────────────────────────────────────────────────────────────
# Hilfsfunktionen
# ─────────────────────────────────────────────────────────────────────────────

def _email_domain(email: str) -> str:
    m = re.search(r"@([\w.-]+)", email or "")
    return m.group(1).lower() if m else ""


def _valid_de_phone(phone: str) -> bool:
    digits = re.sub(r"\D", "", phone or "")
    return len(digits) >= 10 and (digits.startswith("49") or digits.startswith("0"))


def _fetch_url(url: str, timeout: int = 10) -> str:
    if not url:
        return ""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/json,*/*",
            "Accept-Language": "de-DE,de;q=0.9",
        })
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.read(200000).decode("utf-8", errors="replace")
    except Exception:
        return ""
