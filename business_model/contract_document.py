"""Vermittlungsverträge als HTML (Druck/PDF) — Mustervorlage oder lead-spezifisch."""

from __future__ import annotations

import html
import re
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

from business_model.contract_branding import logo_img_html
from billing.provision import calculate_provision
from company_config import COMPANY
from provisions_config import PROVISIONS

BASE_DIR = Path(__file__).resolve().parent.parent
if (BASE_DIR / "templates" / "contract_base.html").is_file():
    template_dir = BASE_DIR / "templates"
else:
    template_dir = BASE_DIR


def _updated_de() -> str:
    raw = datetime.now().strftime("%d. %B %Y")
    months = {
        "January": "Januar", "February": "Februar", "March": "März",
        "April": "April", "May": "Mai", "June": "Juni", "July": "Juli",
        "August": "August", "September": "September", "October": "Oktober",
        "November": "November", "December": "Dezember",
    }
    for en, de in months.items():
        raw = raw.replace(en, de)
    return raw


def _esc(val: Any) -> str:
    return html.escape(str(val or "").strip())


def _render_template(name: str, ctx: dict) -> str:
    """Minimaler Template-Renderer für {{ var }} und {% if %}/{% endif %}."""
    text = (template_dir / name).read_text(encoding="utf-8")

    if "{% extends" in text and "{% block contract %}" in text:
        base = (template_dir / "contract_base.html").read_text(encoding="utf-8")
        start = text.index("{% block contract %}") + len("{% block contract %}")
        end = text.index("{% endblock %}", start)
        contract_body = text[start:end].strip()
        text = base.replace("{% block contract %}{% endblock %}", contract_body)
        text = text.replace("{% block title %}Kaplan Solutions{% endblock %}", ctx.get("title", "Kaplan Solutions"))

    c = ctx.get("c", {})
    p = ctx.get("p", {})
    lead = ctx.get("lead", {})
    updated = ctx.get("updated", "")

    def repl_dot(expr: str) -> str:
        expr = expr.strip()
        if expr.startswith("c."):
            return str(c.get(expr[2:], ""))
        if expr.startswith("p."):
            return str(p.get(expr[2:], ""))
        if expr.startswith("lead."):
            return str(lead.get(expr[5:], ""))
        return ctx.get(expr, "")

    while "{% if " in text:
        i = text.index("{% if ")
        j = text.index("{% endif %}", i)
        chunk = text[i : j + len("{% endif %}")]
        cond_start = chunk.index("{% if ") + len("{% if ")
        cond_end = chunk.index(" %}", cond_start)
        cond = chunk[cond_start:cond_end].strip()
        inner = chunk[cond_end + 3 : chunk.index("{% endif %}")]
        else_part = ""
        if "{% else %}" in inner:
            inner, else_part = inner.split("{% else %}", 1)
        show = False
        if cond.startswith("c."):
            show = bool(c.get(cond[2:], ""))
        elif cond.startswith("p."):
            show = bool(p.get(cond[2:], ""))
        elif cond.startswith("lead."):
            show = bool(lead.get(cond[5:], ""))
        else:
            show = bool(ctx.get(cond, ""))
        text = text[:i] + (inner if show else else_part) + text[j + len("{% endif %}") :]

    while "{{" in text:
        i = text.index("{{")
        j = text.index("}}", i)
        expr = text[i + 2 : j].strip()
        if "&nbsp;" in expr:
            key = expr.replace("&nbsp;", "").strip().split()[0]
            val = repl_dot(key)
            replacement = f"{val}&nbsp;%" if "partner_percent" in expr else val
        else:
            key = expr.split("|")[0].strip()
            replacement = updated if key == "updated" else repl_dot(key)
        text = text[:i] + replacement + text[j + 2 :]

    return text


def _fill_line(value: str) -> str:
    val = _esc(value)
    if val:
        return f'<span class="fill-value">{val}</span>'
    return '<span class="fill-line"></span>'


def _replace_labeled_fields(text: str, fields: list[tuple[str, str]]) -> str:
    for label, value in fields:
        pattern = (
            rf'(<span class="lbl">{re.escape(label)}</span>\s*)<span class="fill-line"></span>'
        )
        text = re.sub(pattern, rf'\1{_fill_line(str(value or ""))}', text, count=1)
        # Legacy single-line format
        text = re.sub(
            rf"({re.escape(label)}\s*)<span class=\"fill-line\"></span>",
            rf"\1{_fill_line(str(value or ''))}",
            text,
            count=1,
        )
    return text


def _replace_partner_party(text: str, lead: dict) -> str:
    return _replace_labeled_fields(text, [
        ("Firma:", lead.get("firma") or lead.get("company") or lead.get("name")),
        ("Rechtsform:", lead.get("rechtsform")),
        ("Vertretung:", lead.get("vertretung") or lead.get("name")),
        ("Vertretungsberechtigt:", lead.get("vertretung") or lead.get("name")),
        ("Anschrift:", lead.get("anschrift") or _format_address(lead)),
        ("E-Mail:", lead.get("email")),
        ("Telefon:", lead.get("telefon")),
        ("USt-IdNr.:", lead.get("ust_id")),
        ("USt-IdNr. / Steuernr.:", lead.get("ust_id")),
    ])


def _replace_bauherr_party(text: str, lead: dict) -> str:
    return _replace_labeled_fields(text, [
        ("Name / Firma:", lead.get("firma") or lead.get("company") or lead.get("name")),
        ("Rechtsform:", lead.get("rechtsform")),
        ("Vertretung:", lead.get("vertretung") or lead.get("name")),
        ("Vertretungsberechtigt:", lead.get("vertretung") or lead.get("name")),
        ("Anschrift:", lead.get("anschrift") or _format_address(lead)),
        ("E-Mail:", lead.get("email")),
        ("Telefon:", lead.get("telefon")),
    ])


def _format_address(lead: dict) -> str:
    parts = [lead.get("street"), lead.get("plz"), lead.get("stadt")]
    return ", ".join(p for p in parts if p)


def _replace_project_block(text: str, project: dict) -> str:
    refs = [
        project.get("ref") or project.get("project_ref"),
        project.get("name") or project.get("project_name"),
        project.get("region") or project.get("stadt"),
    ]
    for val in refs:
        text = text.replace('<span class="fill-line"></span>', _fill_line(str(val or "")), 1)
    return text


def _replace_anlage_table(text: str, anlage: dict) -> str:
    rows = [
        anlage.get("ks_ref") or anlage.get("ref"),
        anlage.get("auftraggeber") or anlage.get("ag_firma"),
        anlage.get("projekt") or anlage.get("project_label"),
        anlage.get("datum") or datetime.now().strftime("%d.%m.%Y"),
        anlage.get("netto_plan") or anlage.get("netto_fmt"),
    ]
    # Anlage table: first column labels, second column values — replace empty td after label rows
    for val in rows:
        text = re.sub(
            r"(<td>&nbsp;</td>)",
            f"<td>{_fill_line(str(val or ''))}</td>",
            text,
            count=1,
        )
    return text


def _provision_summary_html(calc: dict) -> str:
    return f"""
<div class="provision-box">
    <strong>Individuelle Konditionen (Anlage zu § 2)</strong><br />
    Netto-Auftragssumme (Plan): <strong>{_esc(calc['netto_order_fmt'])}&nbsp;€</strong><br />
    Provision ({calc['percent']}&nbsp;% netto, min. {_esc(PROVISIONS['partner_min'])}&nbsp;€,
    max. {_esc(PROVISIONS['partner_max'])}&nbsp;€): <strong>{_esc(calc['provision_net_fmt'])}&nbsp;€ netto</strong><br />
    zzgl. 19&nbsp;% USt: {_esc(calc['vat_amount_fmt'])}&nbsp;€ · <strong>Gesamt: {_esc(calc['gross_total_fmt'])}&nbsp;€ brutto</strong><br />
    <em>Fälligkeit: Einmalzahlung innerhalb von 14 Kalendertagen nach Vertragsschluss, Baubeginn oder erster Anzahlung.</em>
</div>
"""


def _parse_netto(val: Any) -> float:
    raw = str(val or "").strip().replace("€", "").replace(" ", "")
    raw = raw.replace(".", "").replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return 0.0


def build_contract_context(
    *,
    contract_type: str,
    lead: dict | None = None,
    netto_eur: float | None = None,
    project_ref: str = "",
    project_name: str = "",
    region: str = "",
    ag_firma: str = "",
    ag_ref: str = "",
) -> dict:
    lead = dict(lead or {})
    netto = netto_eur if netto_eur is not None else _parse_netto(lead.get("netto") or lead.get("budget"))
    calc = calculate_provision(netto) if netto > 0 else None
    project = {
        "ref": project_ref,
        "name": project_name,
        "region": region or lead.get("stadt") or "",
    }
    anlage = {
        "ks_ref": lead.get("ref") or project_ref,
        "auftraggeber": ag_firma,
        "project_label": " · ".join(x for x in [project_name, region] if x),
        "netto_plan": calc["netto_order_fmt"] + " €" if calc else "",
    }
    if lead.get("ref"):
        anlage["ks_ref"] = lead["ref"]
    return {
        "lead": lead,
        "project": project,
        "anlage": anlage,
        "calc": calc,
        "contract_type": contract_type,
        "ag_ref": ag_ref,
    }


def render_partner_contract_html(
    lead: dict | None = None,
    *,
    netto_eur: float | None = None,
    project_ref: str = "",
    project_name: str = "",
    region: str = "",
    ag_firma: str = "",
    ag_ref: str = "",
) -> str:
    ctx_data = build_contract_context(
        contract_type="partner",
        lead=lead,
        netto_eur=netto_eur,
        project_ref=project_ref,
        project_name=project_name,
        region=region,
        ag_firma=ag_firma,
        ag_ref=ag_ref,
    )
    ctx = {
        "c": COMPANY,
        "p": PROVISIONS,
        "updated": _updated_de(),
        "title": "Vermittlungsvertrag Partner-Unternehmen — Kaplan Solutions",
        "lead": ctx_data["lead"],
        "logo_img": logo_img_html(),
    }
    text = _render_template("vermittlungsvertrag_partner.html", ctx)
    if lead:
        text = _replace_partner_party(text, lead)
    if ctx_data["calc"]:
        text = text.replace(
            "<h2>§ 4 Entstehen des Provisionsanspruchs</h2>",
            _provision_summary_html(ctx_data["calc"]) + '<h2>§ 4 Entstehen des Provisionsanspruchs</h2>',
        )
    if any(ctx_data["anlage"].values()):
        text = _replace_anlage_table(text, ctx_data["anlage"])
    return text


def render_bauherr_contract_html(
    lead: dict | None = None,
    *,
    project_ref: str = "",
    project_name: str = "",
    region: str = "",
    **_: Any,
) -> str:
    ctx_data = build_contract_context(
        contract_type="bauherr",
        lead=lead,
        project_ref=project_ref,
        project_name=project_name,
        region=region,
    )
    ctx = {
        "c": COMPANY,
        "p": PROVISIONS,
        "updated": _updated_de(),
        "title": "Vermittlungsvertrag Bauherr — Kaplan Solutions",
        "lead": ctx_data["lead"],
        "logo_img": logo_img_html(),
    }
    text = _render_template("vermittlungsvertrag_bauherr.html", ctx)
    if lead:
        text = _replace_bauherr_party(text, lead)
    if any(ctx_data["project"].values()):
        text = _replace_project_block(text, ctx_data["project"])
    if ctx_data["project"].get("ref"):
        text = _replace_anlage_table(text, {
            "ks_ref": ctx_data["project"]["ref"],
            "auftraggeber": lead.get("company") or lead.get("name") if lead else "",
            "project_label": ctx_data["project"].get("name") or ctx_data["project"].get("region"),
            "datum": datetime.now().strftime("%d.%m.%Y"),
        })
    return text


def render_contract_html(
    contract_type: str,
    lead: dict | None = None,
    **kwargs: Any,
) -> str:
    if contract_type == "bauherr":
        return render_bauherr_contract_html(lead, **kwargs)
    return render_partner_contract_html(lead, **kwargs)


def write_contract_files(out_dir: Path | None = None) -> list[Path]:
    """Musterverträge (leer) als HTML für PDF-Druck."""
    out_dir = out_dir or BASE_DIR / "data" / "contracts"
    out_dir.mkdir(parents=True, exist_ok=True)
    files = []
    partner = out_dir / "Mustervertrag-Partner.html"
    bauherr = out_dir / "Mustervertrag-Bauherr.html"
    partner.write_text(render_partner_contract_html(), encoding="utf-8")
    bauherr.write_text(render_bauherr_contract_html(), encoding="utf-8")
    files.extend([partner, bauherr])
    return files
