"""Intro nachreichen wenn Partner-Vertrag im CRM auf Ja gesetzt wird."""

from __future__ import annotations

from matching.intro import send_intro_for_match
from sheet_client import sheet_action


def try_intro_after_contract(ref: str, admin_email: str) -> dict | None:
    pair = sheet_action("match_pair_for_ref", {"ref": ref})
    if not pair.get("ok"):
        return None
    match = dict(pair.get("match") or {})
    match["an_vertrag"] = "Ja"
    return send_intro_for_match(match, admin_email=admin_email, force=True)
