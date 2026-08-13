"""Stromversorgung überwachen — ein leerer Akku legt den gesamten Versand still.

Am 13.08. lief das MacBook nachts auf Akku, ging um 09:04 bei 1 % in den
Ruhezustand und blieb den ganzen Tag aus. Aufgefallen ist es erst abends.
Diese Prüfung meldet den Zustand, solange noch Zeit zum Gegensteuern ist.
"""

from __future__ import annotations

import os
import re
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

from outreach import config
from outreach import storage

TZ = ZoneInfo("Europe/Berlin")

WARN_PERCENT = int(os.getenv("OUTREACH_BATTERY_WARN_PERCENT", "35"))
CRITICAL_PERCENT = int(os.getenv("OUTREACH_BATTERY_CRITICAL_PERCENT", "20"))


def battery_state() -> dict | None:
    """Ladestand in Prozent, Netzteil und Ladevorgang. None ohne Akku."""
    try:
        out = subprocess.run(
            ["pmset", "-g", "batt"], capture_output=True, text=True, timeout=10
        ).stdout
    except (FileNotFoundError, subprocess.SubprocessError):
        return None

    match = re.search(r"(\d+)%", out)
    if not match:
        return None
    return {
        "percent": int(match.group(1)),
        "on_ac": "AC Power" in out,
        "charging": "charging" in out and "discharging" not in out,
        "discharging": "discharging" in out,
    }


def charger_watts() -> int | None:
    try:
        out = subprocess.run(
            ["system_profiler", "SPPowerDataType"],
            capture_output=True, text=True, timeout=25,
        ).stdout
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    match = re.search(r"Wattage \(W\):\s*(\d+)", out)
    return int(match.group(1)) if match else None


def _alert(subject: str, text: str) -> bool:
    try:
        from mailer import email_configured, send_email
    except ImportError:
        return False
    to = os.getenv("OUTREACH_ALERT_EMAIL", os.getenv("ADMIN_EMAIL", "")).strip()
    if not to or not email_configured():
        return False
    html = (
        '<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;'
        'line-height:1.6;max-width:560px">'
        f'<h2 style="color:#8a2b00;margin:0 0 12px">{subject}</h2>'
        f'<p style="white-space:pre-wrap">{text}</p></body></html>'
    )
    try:
        send_email(to, subject, text, html)
        return True
    except Exception:
        return False


def check_power(in_window: bool) -> bool:
    """Warnt einmal täglich, wenn der Strom den Versand gefährdet."""
    if not in_window:
        return False
    state = battery_state()
    if not state or state["percent"] >= WARN_PERCENT and state["on_ac"]:
        return False

    day = datetime.now(TZ).date().isoformat()
    percent = state["percent"]
    critical = percent <= CRITICAL_PERCENT
    key = "power_critical" if critical else "power_warn"
    if storage.flag_was_set(day, key):
        return False

    watts = charger_watts()
    if state["discharging"] or not state["on_ac"]:
        lage = "Das Gerät läuft auf Akku, das Netzteil hängt nicht dran."
    elif watts and watts < 60:
        lage = (
            f"Das Netzteil liefert nur {watts} Watt. Das reicht im Betrieb oft nicht "
            "zum Nachladen, der Akku wird trotz Kabel leerer."
        )
    else:
        lage = "Das Gerät hängt am Netzteil, lädt aber nur langsam."

    subject = (
        f"Outreach in Gefahr: Akku bei {percent} %"
        if critical
        else f"Hinweis: Akku bei {percent} %"
    )
    text = (
        f"Akkustand: {percent} %\n{lage}\n\n"
        "Wenn der Akku leer wird, geht der Mac in den Ruhezustand und der Versand "
        "steht sofort still — auch mitten im Sendefenster.\n\n"
        "Bitte ein kräftiges Netzteil anschließen und prüfen, ob der Ladevorgang "
        "wirklich anläuft."
    )
    if _alert(subject, text):
        storage.set_flag(day, key)
        print(f"[outreach] Strom-Warnung verschickt (Akku {percent} %)", flush=True)
        return True
    return False


def report_gap(gap_seconds: float) -> bool:
    """Meldet einen Ausfall, sobald der Rechner wieder da ist."""
    if gap_seconds < 3600:
        return False
    now = datetime.now(TZ)
    if not (config.SEND_HOUR_START <= now.hour < config.SEND_HOUR_END):
        return False

    day = now.date().isoformat()
    if storage.flag_was_set(day, "gap_alert"):
        return False

    hours = gap_seconds / 3600
    state = battery_state()
    akku = f"{state['percent']} %" if state else "unbekannt"
    text = (
        f"Der Outreach-Dienst war {hours:.1f} Stunden nicht aktiv und läuft jetzt "
        f"wieder.\n\nWahrscheinlichste Ursache: Der Mac war im Ruhezustand.\n"
        f"Aktueller Akkustand: {akku}\n\n"
        "Der Nachholversand läuft automatisch an, solange das Sendefenster offen ist."
    )
    if _alert(f"Versand-Ausfall von {hours:.1f} Stunden", text):
        storage.set_flag(day, "gap_alert")
        return True
    return False
