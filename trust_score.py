"""Hintergrund-Seriositätsprüfung via Internet-Recherche."""

from __future__ import annotations

import json
import os
import re
import ssl
import threading
import urllib.error
import urllib.request
from datetime import datetime

USER_AGENT = "Mozilla/5.0 (compatible; KaplanSolutions/1.0)"
FREE_EMAIL_DOMAINS = {
    "gmail.com", "googlemail.com", "yahoo.com", "yahoo.de", "hotmail.com",
    "outlook.com", "live.de", "icloud.com", "gmx.de", "gmx.net", "web.de",
    "t-online.de", "mail.de", "proton.me", "protonmail.com",
}


def schedule_trust_check(payload: dict) -> None:
    """Startet Seriositäts-Prüfung im Hintergrund (blockiert nicht die Antwort)."""
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
            f"[trust] {payload.get('ref')} → {result['score']}% ({result['status']})",
            flush=True,
        )
    except Exception as exc:
        print(f"[trust] Fehler für {payload.get('ref')}: {exc}", flush=True)


def run_trust_check(payload: dict) -> dict:
    """Führt Internet-Checks aus und liefert Score 0–100 mit Details."""
    checks: list[dict] = []
    score = 50  # Basis: Anfrage ist eingegangen

    name = (payload.get("name") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    phone = (payload.get("phone") or "").strip()
    company = (
        payload.get("company_name") or payload.get("company") or ""
    ).strip()
    if company == "—":
        company = ""
    role = payload.get("role") or ""
    message = (payload.get("message") or "").strip()
    domain = _email_domain(email)

    # Firmenname
    if company and company not in ("—", "-"):
        checks.append({"ok": True, "label": "Firmenname angegeben", "pts": 8})
        score += 8
    elif role == "unternehmen":
        checks.append({"ok": False, "label": "Kein Firmenname (Auftragnehmer)", "pts": -10})
        score -= 10

    # E-Mail-Domain
    if domain and domain not in FREE_EMAIL_DOMAINS:
        checks.append({"ok": True, "label": f"Firmen-Domain @{domain}", "pts": 12})
        score += 12
    elif domain in FREE_EMAIL_DOMAINS:
        checks.append({"ok": False, "label": f"Privatmail @{domain}", "pts": -8})
        score -= 8

    # Telefon
    if _valid_de_phone(phone):
        checks.append({"ok": True, "label": "Telefonnummer plausibel (DE)", "pts": 8})
        score += 8
    else:
        checks.append({"ok": False, "label": "Telefon unvollständig", "pts": -5})
        score -= 5

    # Nachricht
    if len(message) >= 30:
        checks.append({"ok": True, "label": "Ausführliche Nachricht", "pts": 5})
        score += 5
    elif len(message) < 10:
        checks.append({"ok": False, "label": "Sehr kurze Nachricht", "pts": -8})
        score -= 8

    # Website + Impressum
    site_score, site_checks = _check_website(domain, company)
    checks.extend(site_checks)
    score += site_score

    # Websuche (optional Serper API)
    search_score, search_checks = _check_web_search(company or name, payload)
    checks.extend(search_checks)
    score += search_score

    score = max(0, min(100, score))
    if score >= 70:
        status = "Seriös"
        flags = "🟢"
    elif score >= 40:
        status = "Prüfen"
        flags = "🟡"
    else:
        status = "Vorsicht"
        flags = "🔴"

    details_lines = [f"Score: {score}% — {status}", ""]
    for c in checks:
        icon = "✅" if c["ok"] else "⚠️"
        details_lines.append(f"{icon} {c['label']} ({c.get('pts', 0):+d})")

    return {
        "score": score,
        "status": status,
        "flags": flags,
        "details": "\n".join(details_lines),
        "checks": checks,
    }


def _check_website(domain: str, company: str) -> tuple[int, list]:
    checks: list[dict] = []
    score = 0
    if not domain or domain in FREE_EMAIL_DOMAINS:
        return 0, checks

    for url in (f"https://{domain}", f"https://www.{domain}"):
        html = _fetch_url(url, timeout=8)
        if not html:
            continue
        checks.append({"ok": True, "label": f"Website erreichbar ({url})", "pts": 10})
        score += 10
        low = html.lower()
        if "impressum" in low or "imprint" in low:
            checks.append({"ok": True, "label": "Impressum-Hinweis auf Website", "pts": 10})
            score += 10
        else:
            checks.append({"ok": False, "label": "Kein Impressum auf Startseite", "pts": -5})
            score -= 5
        if company and company.lower()[:6] in low:
            checks.append({"ok": True, "label": "Firmenname auf Website", "pts": 8})
            score += 8
        break
    else:
        checks.append({"ok": False, "label": "Website nicht erreichbar", "pts": -5})
        score -= 5

    return score, checks


def _check_web_search(query: str, payload: dict) -> tuple[int, list]:
    checks: list[dict] = []
    score = 0
    api_key = os.getenv("SERPER_API_KEY", "").strip()
    if not api_key or not query or len(query) < 3:
        return 0, checks

    city = ""
    if payload.get("role") == "bauherr":
        city = (payload.get("location") or "").split(",")[0].strip()
    else:
        city = (payload.get("region") or "").split(",")[0].strip()

    search_q = f"{query} Bau Unternehmen {city}".strip()
    try:
        body = json.dumps({"q": search_q, "gl": "de", "hl": "de", "num": 5}).encode()
        req = urllib.request.Request(
            "https://google.serper.dev/search",
            data=body,
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode())
        organic = data.get("organic") or []
        if organic:
            checks.append({
                "ok": True,
                "label": f"Google: {len(organic)} Treffer für „{search_q[:40]}“",
                "pts": 10,
            })
            score += 10
            top = organic[0]
            checks.append({
                "ok": True,
                "label": f"Top-Treffer: {top.get('title', '')[:60]}",
                "pts": 5,
            })
            score += 5
        else:
            checks.append({"ok": False, "label": "Keine Google-Treffer", "pts": -10})
            score -= 10
    except Exception as exc:
        checks.append({"ok": False, "label": f"Websuche fehlgeschlagen: {exc}", "pts": 0})

    return score, checks


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
        "details": result["details"],
        "report_url": "",
    }).encode("utf-8")

    headers = {"Content-Type": "application/json", "User-Agent": USER_AGENT}

    def post(target: str) -> None:
        req = urllib.request.Request(target, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
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


def _email_domain(email: str) -> str:
    m = re.search(r"@([\w.-]+)", email or "")
    return m.group(1).lower() if m else ""


def _valid_de_phone(phone: str) -> bool:
    digits = re.sub(r"\D", "", phone or "")
    return len(digits) >= 10 and digits.startswith(("49", "0"))


def _fetch_url(url: str, timeout: int = 8) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.read(80000).decode("utf-8", errors="replace")
    except Exception:
        return ""
