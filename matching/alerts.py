"""Sofort-Benachrichtigung bei qualifiziertem Match (Admin + Bauherr)."""

from __future__ import annotations

from company_config import COMPANY, company_footer_text
from lead_followup.config import AGENT_NAME, REPLY_EMAIL
from matching.alert_store import already_sent, mark_sent
from matching.config import MATCH_ALERT_MIN_SCORE
from mailer import send_email

GOLD = "#b87333"
GREEN = "#0b3d2e"
TEXT = "#1a1a1a"
MUTED = "#666666"

CHECKLIST = [
    ("Partner-Vertrag unterschrieben?", "Falls nein: Mustervertrag senden — kein Intro ohne Unterschrift."),
    ("Match-Ordner in Drive prüfen", "Dokumente & Notizen für diese Vermittlung."),
    ("Intro vorbereiten", "E-Mail an Bauherr + Partner (CC), Anlage „Vermittelter Kontakt“."),
    ("Termin fürs Erstgespräch", "Das machst nur du — Partner und Bauherr zusammenbringen."),
    ("Sheet: Status → „In Kontakt“", "Tab Top Matches / Matches aktualisieren."),
    ("Nach Vertragsschluss", "Partner meldet sich → Rechnung stellen (5 % netto)."),
]


def _safe(s: str) -> str:
    return (
        str(s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _wrap(inner: str) -> str:
    return f"""<!DOCTYPE html><html lang="de"><head><meta charset="utf-8"></head>
<body style="margin:0;background:#f0f0f0;font-family:Arial,Helvetica,sans-serif">
<table width="100%" cellspacing="0" cellpadding="0" style="background:#f0f0f0;padding:28px 12px">
<tr><td align="center">
<table width="640" style="max-width:640px;background:#fff;border:1px solid #e0e0e0">{inner}
</table></td></tr></table></body></html>"""


def _checklist_html() -> str:
    items = ""
    for i, (title, detail) in enumerate(CHECKLIST, 1):
        items += (
            f'<tr><td style="padding:12px 16px;border-bottom:1px solid #eee;vertical-align:top;width:28px">'
            f'<span style="display:inline-block;width:22px;height:22px;border:2px solid {GOLD};border-radius:2px"></span></td>'
            f'<td style="padding:12px 16px;border-bottom:1px solid #eee">'
            f'<strong style="color:{TEXT}">{i}. {_safe(title)}</strong><br>'
            f'<span style="font-size:13px;color:{MUTED}">{_safe(detail)}</span></td></tr>'
        )
    return (
        f'<table width="100%" style="border:1px solid #eee;border-collapse:collapse;margin:16px 0">'
        f'<tr style="background:{GREEN}"><td colspan="2" style="padding:10px 16px;color:#d9b75a;'
        f'font-size:11px;letter-spacing:0.15em;text-transform:uppercase">Deine Checkliste</td></tr>'
        f"{items}</table>"
    )


def _checklist_text() -> str:
    lines = ["DEINE CHECKLISTE:", ""]
    for i, (title, detail) in enumerate(CHECKLIST, 1):
        lines.append(f"  [ ] {i}. {title}")
        lines.append(f"      → {detail}")
    return "\n".join(lines)


def build_admin_alert(match: dict) -> tuple[str, str, str]:
    score = match.get("score", 0)
    ag_name = match.get("ag_firma") or match.get("ag_name") or "Bauherr"
    an_name = match.get("an_firma") or match.get("an_name") or "Partner"
    subject = f"🔥 Heißer Match {score}% — {ag_name} ↔ {an_name} | Jetzt handeln"

    text = f"""HEISSER MATCH — SOFORT-ALERT
Passung: {score}%
Match-ID: {match.get('match_id', '')}

BAUHERR / AUFTRAGGEBER
  Name:   {match.get('ag_name', '')}
  Firma:  {match.get('ag_firma', '')}
  E-Mail: {match.get('ag_email', '')}
  Tel:    {match.get('ag_phone', '—')}
  Ref:    {match.get('ag_ref', '')}

PARTNER-FIRMA
  Name:   {match.get('an_name', '')}
  Firma:  {match.get('an_firma', '')}
  E-Mail: {match.get('an_email', '')}
  Tel:    {match.get('an_phone', '—')}
  Ref:    {match.get('an_ref', '')}

PROJEKT
  Region:  {match.get('stadt', '')}
  Branche: {match.get('branche', '')}
  Warum:   {match.get('reasons', '')}

{_checklist_text()}

Match-Ordner: {match.get('folder_url') or '—'}

Der Bauherr wurde automatisch per E-Mail informiert, dass ein passender Partner gefunden wurde.
Deine Aufgabe: Termin fürs Erstgespräch ausmachen.

{company_footer_text()}
"""
    inner = f"""
<tr><td style="padding:28px 32px 20px;background:{GREEN};border-bottom:3px solid {GOLD}">
  <p style="margin:0 0 6px;font-size:10px;letter-spacing:0.35em;color:{GOLD};text-transform:uppercase">Kaplan Solutions</p>
  <p style="margin:0;font-family:Georgia,serif;font-size:24px;color:#fff;font-weight:400">Heißer Match — {score}%</p>
  <p style="margin:8px 0 0;font-size:13px;color:#c8d4ce">Sofort-Alert · Bauherr wurde benachrichtigt</p>
</td></tr>
<tr><td style="padding:28px 32px">
  <p style="margin:0 0 20px;font-size:15px;color:{TEXT};line-height:1.6">
    Ein <strong>qualifizierter Match</strong> ist bereit zur Vermittlung. Du musst nur das
    <strong>Erstgespräch</strong> führen und den <strong>Partner-Vertrag</strong> sichern — der Rest läuft im Hintergrund.
  </p>
  <table width="100%" style="border-collapse:collapse;font-size:14px;margin-bottom:20px">
    <tr style="background:#f7f7f7"><td colspan="2" style="padding:10px 14px;font-weight:bold;color:{GREEN}">Bauherr / Auftraggeber</td></tr>
    <tr><td style="padding:8px 14px;border-bottom:1px solid #eee;width:30%;color:{MUTED}">Name</td>
        <td style="padding:8px 14px;border-bottom:1px solid #eee"><strong>{_safe(match.get('ag_name',''))}</strong></td></tr>
    <tr><td style="padding:8px 14px;border-bottom:1px solid #eee;color:{MUTED}">Firma</td>
        <td style="padding:8px 14px;border-bottom:1px solid #eee">{_safe(match.get('ag_firma',''))}</td></tr>
    <tr><td style="padding:8px 14px;border-bottom:1px solid #eee;color:{MUTED}">E-Mail</td>
        <td style="padding:8px 14px;border-bottom:1px solid #eee"><a href="mailto:{_safe(match.get('ag_email',''))}" style="color:{GOLD}">{_safe(match.get('ag_email',''))}</a></td></tr>
    <tr><td style="padding:8px 14px;border-bottom:1px solid #eee;color:{MUTED}">Telefon</td>
        <td style="padding:8px 14px;border-bottom:1px solid #eee">{_safe(match.get('ag_phone','—'))}</td></tr>
    <tr><td style="padding:8px 14px;border-bottom:1px solid #eee;color:{MUTED}">Anfrage-Nr.</td>
        <td style="padding:8px 14px;border-bottom:1px solid #eee"><strong style="color:{GOLD}">{_safe(match.get('ag_ref',''))}</strong></td></tr>
    <tr style="background:#f7f7f7"><td colspan="2" style="padding:10px 14px;font-weight:bold;color:{GREEN}">Partner-Firma</td></tr>
    <tr><td style="padding:8px 14px;border-bottom:1px solid #eee;color:{MUTED}">Firma</td>
        <td style="padding:8px 14px;border-bottom:1px solid #eee"><strong>{_safe(match.get('an_firma') or match.get('an_name',''))}</strong></td></tr>
    <tr><td style="padding:8px 14px;border-bottom:1px solid #eee;color:{MUTED}">E-Mail</td>
        <td style="padding:8px 14px;border-bottom:1px solid #eee"><a href="mailto:{_safe(match.get('an_email',''))}" style="color:{GOLD}">{_safe(match.get('an_email',''))}</a></td></tr>
    <tr><td style="padding:8px 14px;border-bottom:1px solid #eee;color:{MUTED}">Telefon</td>
        <td style="padding:8px 14px;border-bottom:1px solid #eee">{_safe(match.get('an_phone','—'))}</td></tr>
    <tr><td style="padding:8px 14px;border-bottom:1px solid #eee;color:{MUTED}">Anfrage-Nr.</td>
        <td style="padding:8px 14px;border-bottom:1px solid #eee">{_safe(match.get('an_ref',''))}</td></tr>
    <tr style="background:#f7f7f7"><td colspan="2" style="padding:10px 14px;font-weight:bold;color:{GREEN}">Passung</td></tr>
    <tr><td style="padding:8px 14px;color:{MUTED}">Region / Branche</td>
        <td style="padding:8px 14px">{_safe(match.get('stadt',''))} · {_safe(match.get('branche',''))}</td></tr>
    <tr><td style="padding:8px 14px;color:{MUTED}">Gründe</td>
        <td style="padding:8px 14px">{_safe(match.get('reasons',''))}</td></tr>
  </table>
  {_checklist_html()}
  {'<p style="margin:16px 0 0"><a href="' + _safe(match.get('folder_url','')) + '" style="color:' + GOLD + '">→ Match-Ordner in Drive öffnen</a></p>' if match.get('folder_url') else ''}
</td></tr>
<tr><td style="padding:16px 32px;background:#fafafa;border-top:1px solid #eee;font-size:12px;color:#888">
  {company_footer_text().replace(chr(10), '<br>')}
</td></tr>"""
    return subject, text, _wrap(inner)


def build_bauherr_match_notice(match: dict) -> tuple[str, str, str]:
    name = (match.get("ag_name") or "").strip() or "Sehr geehrte Damen und Herren"
    greeting = name if name.startswith(("Sehr", "Herr", "Frau")) else f"Sehr geehrte/r {name}"
    ref = match.get("ag_ref") or ""
    partner = match.get("an_firma") or match.get("an_name") or "ein geprüftes Partnerunternehmen"
    ref_line = f" (Anfrage-Nr. {ref})" if ref else ""
    subject = f"Gute Nachricht — passender Partner gefunden{ref_line}"

    text = f"""{greeting},

wir haben freundliche Nachrichten zu Ihrer Anfrage bei Kaplan Solutions.

Für Ihr Projekt haben wir einen passenden Partner in unserem Netzwerk identifiziert:
{partner} — Region: {match.get('stadt', '')}, Gewerk: {match.get('branche', '')}.

Wir melden uns in Kürze persönlich bei Ihnen, um einen Termin für ein
Erstgespräch zu vereinbaren. In diesem Gespräch stellen wir Ihnen den Partner
vor und besprechen die nächsten Schritte.

{f'Ihre Anfrage-Nr.: {ref}' + chr(10) if ref else ''}
Bei Rückfragen erreichen Sie uns jederzeit:
E-Mail: {REPLY_EMAIL}
Telefon: {COMPANY['phone']}

Mit freundlichen Grüßen

{AGENT_NAME}
{company_footer_text()}
"""
    inner = f"""
<tr><td style="padding:36px 40px 24px;border-bottom:1px solid #e8e8e8">
  <p style="margin:0 0 12px;font-size:11px;letter-spacing:0.35em;text-transform:uppercase;color:{GOLD}">Kaplan Solutions</p>
  <p style="margin:0;font-family:Georgia,serif;font-size:24px;color:{TEXT};line-height:1.35">Passender Partner gefunden</p>
</td></tr>
<tr><td style="padding:32px 40px;font-size:15px;line-height:1.75;color:{MUTED}">
  <p style="margin:0 0 20px;color:{TEXT}">{_safe(greeting)},</p>
  <p style="margin:0 0 20px">wir haben <strong style="color:{TEXT}">gute Nachrichten</strong> zu Ihrer Anfrage bei Kaplan Solutions.</p>
  <p style="margin:0 0 20px">Für Ihr Projekt haben wir einen passenden Partner identifiziert:
  <strong style="color:{TEXT}">{_safe(partner)}</strong>
  — {_safe(match.get('stadt',''))}, {_safe(match.get('branche',''))}.</p>
  <p style="margin:0 0 28px">Wir melden uns <strong>in Kürze persönlich</strong> bei Ihnen, um einen Termin für ein
  Erstgespräch zu vereinbaren. Dort stellen wir Ihnen den Partner vor und besprechen die nächsten Schritte.</p>
  {'<p style="margin:0 0 24px;font-size:14px;color:' + MUTED + '">Anfrage-Nr.: <strong style="color:' + GOLD + '">' + _safe(ref) + '</strong></p>' if ref else ''}
  <table width="100%" style="background:#f7f7f7;border:1px solid #ebebeb;margin-bottom:28px">
  <tr><td style="padding:20px 24px">
    <p style="margin:0 0 8px;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:{GOLD}">Nächster Schritt</p>
    <p style="margin:0;font-size:14px;color:{TEXT}">Wir kontaktieren Sie zeitnah für die Terminvereinbarung.</p>
  </td></tr></table>
  <p style="margin:0;font-size:14px;color:{MUTED}">
    E-Mail: <a href="mailto:{_safe(REPLY_EMAIL)}" style="color:{GOLD};text-decoration:none">{_safe(REPLY_EMAIL)}</a><br>
    Telefon: {_safe(COMPANY['phone'])}
  </p>
</td></tr>
<tr><td style="padding:0 40px 36px;font-size:12px;color:#aaa;border-top:1px solid #e8e8e8">
  <p style="margin:24px 0 0">{_safe(company_footer_text()).replace(chr(10), '<br>')}</p>
</td></tr>"""
    return subject, text, _wrap(inner)


def process_match_alert(match: dict, *, admin_email: str, force: bool = False) -> dict:
    """Sendet Admin- + Bauherr-Mail bei qualifiziertem Match (idempotent)."""
    match_id = str(match.get("match_id") or "").strip()
    score = int(match.get("score") or 0)
    if score < MATCH_ALERT_MIN_SCORE:
        return {"ok": False, "skipped": "score_below_threshold"}
    if not match_id:
        return {"ok": False, "error": "match_id fehlt"}
    if not force and already_sent(match_id):
        return {"ok": True, "skipped": "already_sent", "match_id": match_id}

    ag_email = (match.get("ag_email") or "").strip()
    if not ag_email:
        return {"ok": False, "error": "ag_email fehlt"}

    admin_subj, admin_text, admin_html = build_admin_alert(match)
    send_email(admin_email, admin_subj, admin_text, admin_html)

    bh_subj, bh_text, bh_html = build_bauherr_match_notice(match)
    send_email(ag_email, bh_subj, bh_text, bh_html, reply_to=REPLY_EMAIL)

    mark_sent(match_id)
    return {"ok": True, "match_id": match_id, "admin": admin_email, "bauherr": ag_email}
