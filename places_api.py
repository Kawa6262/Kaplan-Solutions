"""Google Places API (New) — gemeinsamer Client für Outreach und Trust-Score."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"


def api_key() -> str:
    return os.getenv("GOOGLE_PLACES_API_KEY", "").strip()


def _display_name(place: dict) -> str:
    display = place.get("displayName") or {}
    if isinstance(display, dict):
        return (display.get("text") or "").strip()
    return str(display).strip()


def _request(
    url: str,
    *,
    method: str,
    field_mask: str,
    body: dict | None = None,
    timeout: int = 20,
) -> dict:
    key = api_key()
    if not key:
        return {"error": {"message": "GOOGLE_PLACES_API_KEY fehlt"}}

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": field_mask,
    }
    data = json.dumps(body or {}).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"error": {"message": raw, "code": exc.code}}


def text_search(
    text_query: str,
    page_token: str | None = None,
) -> tuple[list[dict], str | None, str | None]:
    """Text Search (New). Returns (results, next_page_token, error_message)."""
    body: dict[str, str] = {
        "textQuery": text_query,
        "languageCode": "de",
        "regionCode": "DE",
    }
    if page_token:
        body["pageToken"] = page_token

    data = _request(
        SEARCH_URL,
        method="POST",
        field_mask="places.id,places.displayName,places.websiteUri,places.nationalPhoneNumber",
        body=body,
    )
    if data.get("error"):
        err = data["error"]
        return [], None, err.get("message") or str(err)

    results: list[dict] = []
    for place in data.get("places") or []:
        place_id = (place.get("id") or "").strip()
        name = _display_name(place)
        if not place_id or not name:
            continue
        results.append({
            "place_id": place_id,
            "name": name,
            "website": (place.get("websiteUri") or "").strip(),
            "phone": (place.get("nationalPhoneNumber") or "").strip(),
        })

    return results, data.get("nextPageToken"), None


def lookup_ratings(company: str, city: str) -> tuple[float | None, int, str]:
    """Findet Google-Bewertung für eine Firma. Returns (rating, count, maps_url)."""
    query = f"{company} {city}".strip()
    if not query or not api_key():
        return None, 0, ""

    data = _request(
        SEARCH_URL,
        method="POST",
        field_mask="places.rating,places.userRatingCount,places.googleMapsUri",
        body={
            "textQuery": query,
            "languageCode": "de",
            "regionCode": "DE",
        },
        timeout=10,
    )
    if data.get("error"):
        return None, 0, ""

    places = data.get("places") or []
    if not places:
        return None, 0, ""

    place = places[0]
    rating = place.get("rating")
    count = place.get("userRatingCount", 0)
    maps_url = (place.get("googleMapsUri") or "").strip()
    if rating is not None:
        return float(rating), int(count or 0), maps_url
    return None, 0, maps_url
