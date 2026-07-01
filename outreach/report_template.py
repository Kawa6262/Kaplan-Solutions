"""Professionelles Tagesfazit für den Outreach-Betrieb."""

from __future__ import annotations

from company_config import COMPANY, company_footer_text

GOLD = "#c9a227"
GOLD_DIM = "#a88620"
TEXT = "#f0f0f0"
MUTED = "#b0b0b0"
BG = "#0a0a0a"
CARD = "#141414"
BORDER = "#2a2a2a"
SUCCESS = "#4ade80"
WARN = "#fbbf24"
ERROR = "#f87171"


def _safe(s: str) -> str:
    return (
        str(s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _kpi(label: str, value: str | int, sub: str = "", accent: str = GOLD) -> str:
    return f"""
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:{CARD};border:1px solid {BORDER}">
<tr><td style="padding:18px 16px;text-align:center">
  <p style="margin:0 0 6px;font-family:Arial,sans-serif;font-size:28px;font-weight:700;color:{accent};line-height:1">{_safe(str(value))}</p>
  <p style="margin:0 0 4px;font-family:Arial,sans-serif;font-size:11px;letter-spacing:0.14em;text-transform:uppercase;color:{GOLD}">{_safe(label)}</p>
  <p style="margin:0;font-family:Arial,sans-serif;font-size:11px;color:#777">{_safe(sub)}</p>
</td></tr>
</table>"""


def _kpi_row(items: list[tuple[str, str | int, str, str]]) -> str:
    cells = []
    width = max(1, len(items))
    pct = int(100 / width)
    for label, value, sub, accent in items:
        cells.append(
            f'<td width="{pct}%" valign="top" style="padding:4px">{_kpi(label, value, sub, accent)}</td>'
        )
    return f'<tr>{"".join(cells)}</tr>'


def _companies_table(rows: list[dict], empty_msg: str) -> str:
    if not rows:
        return f'<p style="margin:0;font-family:Arial,sans-serif;font-size:14px;color:{MUTED}">{_safe(empty_msg)}</p>'

    body = []
    for i, r in enumerate(rows, 1):
        bg = CARD if i % 2 else "#111"
        body.append(f"""
<tr style="background:{bg}">
  <td style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;color:{TEXT};border-bottom:1px solid {BORDER}">{i}</td>
  <td style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;color:{TEXT};border-bottom:1px solid {BORDER}"><strong>{_safe(r.get("name", ""))}</strong></td>
  <td style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;color:{MUTED};border-bottom:1px solid {BORDER}">{_safe(r.get("city", ""))}</td>
  <td style="padding:12px 14px;font-family:Arial,sans-serif;font-size:12px;color:{MUTED};border-bottom:1px solid {BORDER}">{_safe(r.get("trade", ""))}</td>
  <td style="padding:12px 14px;font-family:Arial,sans-serif;font-size:12px;color:{GOLD};border-bottom:1px solid {BORDER}">{_safe(r.get("email", ""))}</td>
  <td style="padding:12px 14px;font-family:Arial,sans-serif;font-size:12px;color:#888;border-bottom:1px solid {BORDER};white-space:nowrap">{_safe(r.get("time", ""))}</td>
</tr>""")

    return f"""
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border:1px solid {BORDER};margin-top:8px">
<tr style="background:#1a1a1a">
  <th style="padding:10px 14px;font-family:Arial,sans-serif;font-size:10px;letter-spacing:0.12em;text-transform:uppercase;color:{GOLD};text-align:left;border-bottom:1px solid {BORDER}">#</th>
  <th style="padding:10px 14px;font-family:Arial,sans-serif;font-size:10px;letter-spacing:0.12em;text-transform:uppercase;color:{GOLD};text-align:left;border-bottom:1px solid {BORDER}">Firma</th>
  <th style="padding:10px 14px;font-family:Arial,sans-serif;font-size:10px;letter-spacing:0.12em;text-transform:uppercase;color:{GOLD};text-align:left;border-bottom:1px solid {BORDER}">Stadt</th>
  <th style="padding:10px 14px;font-family:Arial,sans-serif;font-size:10px;letter-spacing:0.12em;text-transform:uppercase;color:{GOLD};text-align:left;border-bottom:1px solid {BORDER}">Gewerk</th>
  <th style="padding:10px 14px;font-family:Arial,sans-serif;font-size:10px;letter-spacing:0.12em;text-transform:uppercase;color:{GOLD};text-align:left;border-bottom:1px solid {BORDER}">E-Mail</th>
  <th style="padding:10px 14px;font-family:Arial,sans-serif;font-size:10px;letter-spacing:0.12em;text-transform:uppercase;color:{GOLD};text-align:left;border-bottom:1px solid {BORDER}">Uhrzeit</th>
</tr>
{"".join(body)}
</table>"""


def _bar_list(items: list[dict], key: str, label_key: str = "label") -> str:
    if not items:
        return f'<p style="margin:0;font-size:13px;color:{MUTED}">Keine Daten</p>'
    max_c = max(int(x.get(key, 0)) for x in items) or 1
    rows = []
    for item in items[:8]:
        count = int(item.get(key, 0))
        pct = max(4, int(count / max_c * 100))
        rows.append(f"""
<tr><td style="padding:6px 0;font-family:Arial,sans-serif;font-size:13px;color:{MUTED}">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
  <tr>
    <td width="38%" style="color:{TEXT};font-size:13px">{_safe(item.get(label_key, ""))}</td>
    <td>
      <div style="background:#222;height:8px;border-radius:4px;overflow:hidden">
        <div style="background:{GOLD};width:{pct}%;height:8px;border-radius:4px"></div>
      </div>
    </td>
    <td width="36px" align="right" style="color:{GOLD};font-size:12px;font-weight:700">{count}</td>
  </tr>
  </table>
</td></tr>""")
    return f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0">{"".join(rows)}</table>'


def build_daily_report(data: dict) -> tuple[str, str, str]:
    brand = COMPANY.get("brand", "Kaplan Solutions")
    date_label = data.get("date_label", "")
    sent = int(data.get("sent_today", 0))
    total_sent = int(data.get("total_sent_today", sent))
    total_limit = int(data.get("total_sent_limit", data.get("sent_limit", 40)))
    subject = f"Outreach Tagesfazit · {date_label} · {total_sent} Firmen kontaktiert"

    companies = data.get("companies_sent") or []
    failed = data.get("companies_failed") or []

    text_companies = "\n".join(
        f"  {i}. {r.get('name')} · {r.get('city')} · {r.get('email')} · {r.get('time')}"
        for i, r in enumerate(companies, 1)
    ) or "  (keine Versände heute)"

    text_failed = "\n".join(
        f"  • {r.get('name')} — {r.get('error', '')[:80]}"
        for r in failed
    )

    text = f"""{brand} — Outreach Tagesfazit
{date_label}

KENNZAHLEN HEUTE
  Kontaktiert (gesamt): {total_sent} / {total_limit}
  Partner:              {sent} / {data.get('sent_limit')}
  Referral:             {data.get('referral_sent_today', 0)} / {data.get('referral_sent_limit', 0)}
  Bauherr:              {data.get('bauherr_sent_today', 0)} / {data.get('bauherr_sent_limit', 0)}
  Firmen gefunden:      {data.get('discovered_today')} / {data.get('discover_limit')}
  E-Mails extrahiert:   {data.get('enriched_today')}
  Fehlgeschlagen:       {data.get('failed_today')}
  Übersprungen:         {data.get('skipped_today')}

GESAMTSTAND
  Kontaktiert (gesamt): {data.get('sent_all_time')}
  In Warteschlange:     {data.get('queued')}
  Prospects in DB:      {data.get('total_prospects')}
  Abmeldungen:          {data.get('unsubscribes')}

KONTAKTIERTE FIRMEN HEUTE
{text_companies}

{f'FEHLGESCHLAGEN{chr(10)}{text_failed}{chr(10)}' if failed else ''}
SUCHFORTSCHRITT: {data.get('search_progress', '—')}
{f"REFERRAL HEUTE: {data.get('referral_sent_today', 0)} / {data.get('referral_sent_limit', 15)} · {data.get('referral_search_progress', '—')}{chr(10)}" if data.get('referral_enabled') else ''}AUSBLICK MORGEN: Bis zu {data.get('sent_limit')} weitere Kontakte möglich · {data.get('queued')} in Warteschlange

{company_footer_text()}
"""

    sent_pct = min(100, int(total_sent / max(1, total_limit) * 100))
    status_color = SUCCESS if total_sent > 0 else WARN
    status_text = "Aktiver Tag" if total_sent > 0 else "Keine Versände — System lief trotzdem"

    inner = f"""
<tr><td style="padding:28px 40px 8px;font-family:Georgia,serif;font-size:24px;color:{GOLD};letter-spacing:0.03em">Outreach Tagesfazit</td></tr>
<tr><td style="padding:0 40px 20px;font-family:Arial,sans-serif;font-size:13px;color:#888">{_safe(date_label)}</td></tr>

<tr><td style="padding:0 40px 24px">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:{CARD};border:1px solid {BORDER}">
  <tr><td style="padding:16px 20px">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
    <tr>
      <td style="font-family:Arial,sans-serif;font-size:13px;color:{MUTED}">Tagesstatus</td>
      <td align="right" style="font-family:Arial,sans-serif;font-size:12px;font-weight:700;color:{status_color}">{_safe(status_text)}</td>
    </tr>
    <tr><td colspan="2" style="padding-top:10px">
      <div style="background:#222;height:6px;border-radius:3px;overflow:hidden">
        <div style="background:{GOLD};width:{sent_pct}%;height:6px;border-radius:3px"></div>
      </div>
      <p style="margin:8px 0 0;font-family:Arial,sans-serif;font-size:11px;color:#777">{total_sent} von {total_limit} Tages-Kontakten genutzt ({sent_pct}%) · Partner {sent}/{data.get('sent_limit')}</p>
    </td></tr>
    </table>
  </td></tr>
  </table>
</td></tr>

<tr><td style="padding:0 40px 8px">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
  {_kpi_row([
      ("Kontaktiert", total_sent, f"Limit {total_limit}", GOLD),
      ("Partner", sent, f"Limit {data.get('sent_limit')}", TEXT),
      ("Referral", data.get("referral_sent_today", 0), f"Limit {data.get('referral_sent_limit', 0)}", TEXT),
  ])}
  </table>
</td></tr>

<tr><td style="padding:8px 40px 24px">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
  {_kpi_row([
      ("Bauherr", data.get("bauherr_sent_today", 0), f"Limit {data.get('bauherr_sent_limit', 0)}", TEXT),
      ("Gefunden", data.get("discovered_today", 0), f"Limit {data.get('discover_limit')}", TEXT),
      ("Extrahiert", data.get("enriched_today", 0), "E-Mail-Adressen", TEXT),
  ])}
  </table>
</td></tr>

<tr><td style="padding:8px 40px 24px">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
  {_kpi_row([
      ("Warteschlange", data.get("queued", 0), "bereit zum Versand", GOLD_DIM),
      ("Gesamt kontaktiert", data.get("sent_all_time", 0), "seit Start", TEXT),
      ("Fehler heute", data.get("failed_today", 0), f"{data.get('skipped_today', 0)} übersprungen", ERROR if data.get('failed_today') else MUTED),
  ])}
  </table>
</td></tr>

<tr><td style="padding:0 40px 12px">
  <p style="margin:0;font-family:Arial,sans-serif;font-size:11px;letter-spacing:0.16em;text-transform:uppercase;color:{GOLD}">Kontaktierte Firmen heute</p>
</td></tr>
<tr><td style="padding:0 40px 28px">
  {_companies_table(companies, "Heute wurden noch keine Firmen kontaktiert.")}
</td></tr>
"""

    if failed:
        inner += f"""
<tr><td style="padding:0 40px 12px">
  <p style="margin:0;font-family:Arial,sans-serif;font-size:11px;letter-spacing:0.16em;text-transform:uppercase;color:{ERROR}">Fehlgeschlagene Versuche</p>
</td></tr>
<tr><td style="padding:0 40px 28px">
  {_companies_table(failed, "")}
</td></tr>
"""

    inner += f"""
<tr><td style="padding:0 40px 28px">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
  <tr>
    <td width="48%" valign="top" style="padding-right:12px">
      <p style="margin:0 0 12px;font-family:Arial,sans-serif;font-size:11px;letter-spacing:0.14em;text-transform:uppercase;color:{GOLD}">Top Städte heute</p>
      {_bar_list(data.get("by_city") or [], "count", "city")}
    </td>
    <td width="4%"></td>
    <td width="48%" valign="top" style="padding-left:12px">
      <p style="margin:0 0 12px;font-family:Arial,sans-serif;font-size:11px;letter-spacing:0.14em;text-transform:uppercase;color:{GOLD}">Top Gewerke heute</p>
      {_bar_list(data.get("by_trade") or [], "count", "trade")}
    </td>
  </tr>
  </table>
</td></tr>

<tr><td style="padding:0 40px 28px">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:{CARD};border:1px solid {BORDER}">
  <tr><td style="padding:18px 20px;font-family:Arial,sans-serif;font-size:14px;line-height:1.65;color:{MUTED}">
    <p style="margin:0 0 8px;color:{GOLD};font-size:11px;letter-spacing:0.14em;text-transform:uppercase">Ausblick</p>
    <p style="margin:0 0 8px"><strong style="color:{TEXT}">Morgen:</strong> Bis zu <strong style="color:{GOLD}">{total_limit}</strong> weitere Kontakte · <strong style="color:{TEXT}">{data.get('queued')}</strong> Firmen in der Warteschlange</p>
    <p style="margin:0 0 8px"><strong style="color:{TEXT}">Heute Partner:</strong> {sent} · Referral: {data.get("referral_sent_today", 0)} · Bauherr: {data.get("bauherr_sent_today", 0)}</p>
    <p style="margin:0 0 8px"><strong style="color:{TEXT}">Suche:</strong> {_safe(data.get('search_progress', '—'))}</p>
    {f'<p style="margin:0 0 8px"><strong style="color:{TEXT}">Referral heute:</strong> {data.get("referral_sent_today", 0)} / {data.get("referral_sent_limit", 15)} · {_safe(data.get("referral_search_progress", "—"))}</p>' if data.get('referral_enabled') else ''}
    <p style="margin:0"><strong style="color:{TEXT}">Abmeldungen gesamt:</strong> {data.get('unsubscribes', 0)}</p>
  </td></tr>
  </table>
</td></tr>
"""

    html = f"""<!DOCTYPE html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:{BG}">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:{BG}">
<tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="640" cellspacing="0" cellpadding="0" style="background:#111;border:1px solid {BORDER};max-width:640px">
<tr><td style="padding:24px 40px 0;font-family:Georgia,serif;font-size:14px;color:#666;letter-spacing:0.1em">{_safe(brand)}</td></tr>
{inner}
<tr><td style="padding:20px 40px 32px;font-family:Arial,sans-serif;font-size:11px;color:#666;border-top:1px solid {BORDER};line-height:1.55">
  Automatisches Tagesfazit · Outreach-System<br>
  {_safe(company_footer_text())}
</td></tr>
</table></td></tr></table></body></html>"""

    return subject, text, html
