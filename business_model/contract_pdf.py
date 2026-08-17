"""HTML-Vermittlungsvertrag → PDF (Handy, E-Mail, CRM)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_PDF_STYLE = """<style>
@page { size: A4; margin: 18mm 16mm; }
body { font-family: Helvetica, Arial, sans-serif; font-size: 10pt; color: #222; line-height: 1.45; }
h1, h2, h3 { color: #1a1a1a; page-break-after: avoid; }
.contract-wrap, .page, .contract-page {
  width: 100% !important; max-width: 100% !important; margin: 0 !important;
  box-shadow: none !important; border: none !important;
}
.no-print, button, .print-bar { display: none !important; }
table { width: 100%; border-collapse: collapse; }
.fill-line { border-bottom: 1px solid #333; min-width: 120px; display: inline-block; }
.fill-value { font-weight: 600; }
.logo img { max-height: 48px; width: auto; }
</style>"""


def _strip_for_xhtml2pdf(html: str) -> str:
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.S | re.I)
    html = re.sub(r"<button[^>]*>.*?</button>", "", html, flags=re.S | re.I)
    if "</head>" in html:
        return html.replace("</head>", _PDF_STYLE + "</head>", 1)
    return _PDF_STYLE + html


def html_to_pdf_bytes(html: str, *, base_url: str | None = None) -> tuple[bytes | None, str]:
    """PDF bytes + engine name ('weasyprint' | 'xhtml2pdf' | '')."""
    base = base_url or str(ROOT)

    try:
        from weasyprint import HTML

        pdf = HTML(string=html, base_url=base).write_pdf()
        if pdf and len(pdf) > 500:
            return pdf, "weasyprint"
    except Exception:
        pass

    try:
        from io import BytesIO

        from xhtml2pdf import pisa

        out = BytesIO()
        err = pisa.CreatePDF(_strip_for_xhtml2pdf(html), dest=out, encoding="utf-8")
        pdf = out.getvalue()
        if not err.err and pdf and len(pdf) > 500:
            return pdf, "xhtml2pdf"
    except Exception:
        pass

    return None, ""


def pdf_filename_for(contract_type: str, ref: str) -> str:
    kind = "Partner" if contract_type == "partner" else "Bauherr"
    base = f"Kaplan-Solutions-Vermittlungsvertrag-{kind}"
    if ref:
        base += f"-{ref}"
    return base + ".pdf"
