"""Marken-Assets für Verträge (Logo, Farben, eingebettetes PNG für PDF/E-Mail)."""

from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

from company_config import COMPANY

ROOT = Path(__file__).resolve().parent.parent
LOGO_PATH = ROOT / "email-logo.png"
SITE = COMPANY.get("website", "https://kaplan-solutions.de").rstrip("/")

GREEN = "#0b3d2e"
GOLD = "#b87333"
GOLD_DARK = "#9a6328"
GOLD_LIGHT = "#d4a574"
TEXT = "#1a1a1a"
MUTED = "#5c5c5c"
BORDER = "#d4d4d4"
LOGO_CID = "ks-logo"


@lru_cache(maxsize=1)
def logo_data_uri() -> str:
    if LOGO_PATH.is_file():
        raw = LOGO_PATH.read_bytes()
        return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")
    return f"{SITE}/email-logo.png"


def logo_img_html(*, height: int = 56, css_class: str = "ks-logo") -> str:
    return (
        f'<img src="{logo_data_uri()}" alt="Kaplan Solutions" '
        f'class="{css_class}" height="{height}" '
        f'style="height:{height}px;width:auto;max-width:min(320px,90vw);display:block" />'
    )


def logo_public_url() -> str:
    return f"{SITE}/email-logo.png"


def email_logo_block(*, width: int = 420) -> str:
    """Logo für E-Mail — cid:inline (Gmail blockiert data: URIs)."""
    height = round(width * 100 / 560)
    return (
        f'<img src="cid:{LOGO_CID}" alt="Kaplan Solutions" width="{width}" height="{height}" '
        f'style="display:block;width:{width}px;max-width:100%;height:auto;border:0;outline:none" />'
    )


def logo_email_attachment() -> dict | None:
    """Inline-Anhang für Resend/SMTP (content_id → cid:ks-logo in HTML)."""
    if not LOGO_PATH.is_file():
        return None
    return {
        "filename": "kaplan-solutions-logo.png",
        "content": base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii"),
        "content_id": LOGO_CID,
    }


def email_letterhead_html() -> str:
    """Seriöser Briefkopf für transaktionale Vertrags-Mails."""
    return f"""
<tr><td style="padding:32px 36px 24px;background:#fdfcfa;border-bottom:1px solid #e8e4dc">
  {email_logo_block(width=420)}
  <p style="margin:14px 0 0;font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:1.55;color:{MUTED}">
    {_esc_company_line()}
  </p>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-top:18px">
    <tr>
      <td style="height:3px;background:{GOLD};font-size:0;line-height:0">&nbsp;</td>
      <td width="56" style="height:3px;background:{GOLD_LIGHT};font-size:0;line-height:0">&nbsp;</td>
    </tr>
  </table>
</td></tr>"""


def _esc_company_line() -> str:
    from html import escape
    parts = [
        escape(COMPANY.get("legal_name", "Kaplan Solutions")),
        escape(COMPANY.get("street", "")),
        escape(COMPANY.get("zip_city", "")),
    ]
    line = " · ".join(p for p in parts if p)
    contact = f'{COMPANY.get("email", "")} · {COMPANY.get("phone", "")}'
    return f"{line}<br>{escape(contact)}"
