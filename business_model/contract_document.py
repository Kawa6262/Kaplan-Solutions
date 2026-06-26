"""Standalone Mustervertrag als HTML (E-Mail-Anhang / PDF-Druck)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

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


def _render_template(name: str, ctx: dict) -> str:
    """Minimaler Template-Renderer für {{ var }} und {% if %}/{% endif %}."""
    text = (template_dir / name).read_text(encoding="utf-8")

    # extends + block (nur contract_base → contract)
    if "{% extends" in text and "{% block contract %}" in text:
        base = (template_dir / "contract_base.html").read_text(encoding="utf-8")
        start = text.index("{% block contract %}") + len("{% block contract %}")
        end = text.index("{% endblock %}", start)
        contract_body = text[start:end].strip()
        text = base.replace("{% block contract %}{% endblock %}", contract_body)
        text = text.replace("{% block title %}Kaplan Solutions{% endblock %}", ctx.get("title", "Kaplan Solutions"))

    c = ctx.get("c", {})
    p = ctx.get("p", {})
    updated = ctx.get("updated", "")

    def repl_dot(expr: str) -> str:
        expr = expr.strip()
        if expr.startswith("c."):
            return str(c.get(expr[2:], ""))
        if expr.startswith("p."):
            return str(p.get(expr[2:], ""))
        return ctx.get(expr, "")

    # {% if c.vat_id %}...{% endif %}
    while "{% if " in text:
        i = text.index("{% if ")
        j = text.index("{% endif %}", i)
        chunk = text[i : j + len("{% endif %}")]
        cond_start = chunk.index("{% if ") + len("{% if ")
        cond_end = chunk.index(" %}", cond_start)
        cond = chunk[cond_start:cond_end].strip()
        inner = chunk[cond_end + 3 : chunk.index("{% endif %}")]
        show = False
        if cond.startswith("c."):
            show = bool(c.get(cond[2:], ""))
        elif cond.startswith("p."):
            show = bool(p.get(cond[2:], ""))
        text = text[:i] + (inner if show else "") + text[j + len("{% endif %}") :]

    # {{ var }} und {{ var|nbsp }} etc.
    while "{{" in text:
        i = text.index("{{")
        j = text.index("}}", i)
        expr = text[i + 2 : j].strip()
        if "&nbsp;" in expr:
            expr = expr.replace("&nbsp;", "").strip()
            val = repl_dot(expr.split()[0] if " " in expr else expr)
            if expr.endswith("%"):
                val = repl_dot(expr.split()[0])
            replacement = f"{val}&nbsp;%" if "%" in text[i:j] and "partner_percent" in expr else val
        else:
            key = expr.split("|")[0].strip()
            replacement = updated if key == "updated" else repl_dot(key)
        text = text[:i] + replacement + text[j + 2 :]

    return text


def render_partner_contract_html() -> str:
    ctx = {
        "c": COMPANY,
        "p": PROVISIONS,
        "updated": _updated_de(),
        "title": "Vermittlungsvertrag Partner-Unternehmen — Kaplan Solutions",
    }
    return _render_template("vermittlungsvertrag_partner.html", ctx)
