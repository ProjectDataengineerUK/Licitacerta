from __future__ import annotations

import datetime
from dataclasses import dataclass
from decimal import Decimal
from io import BytesIO
from typing import Literal


@dataclass
class TenantMeta:
    name: str
    cnpj: str
    logo_png_b64: str | None = None  # base64 PNG; None = placeholder


@dataclass
class ProposalContent:
    content: str
    price: Decimal
    validity_days: int
    generated_at: datetime.datetime


VERTICAL = Literal["geral", "ti", "limpeza", "obras"]

PLACEHOLDERS = {
    "EMPRESA": lambda m, _c: m.name,
    "CNPJ": lambda m, _c: m.cnpj,
    "DATA_GERACAO": lambda _m, c: c.generated_at.strftime("%d/%m/%Y %H:%M UTC"),
    "PRECO": lambda _m, c: f"R$ {c.price:,.2f}",
    "VALIDADE_DIAS": lambda _m, c: str(c.validity_days),
    "CONTENT": lambda _m, c: c.content,
}


class ProposalExporter:
    def render_docx(
        self,
        content: ProposalContent,
        vertical: VERTICAL,
        tenant: TenantMeta,
    ) -> BytesIO:
        from pathlib import Path

        from docx import Document

        template_path = (
            Path(__file__).parent.parent / "templates" / "proposal" / f"template_{vertical}.docx"
        )
        doc = Document(template_path)

        subs = {k: fn(tenant, content) for k, fn in PLACEHOLDERS.items()}

        for para in doc.paragraphs:
            for key, val in subs.items():
                if f"{{{{{key}}}}}" in para.text:
                    for run in para.runs:
                        run.text = run.text.replace(f"{{{{{key}}}}}", val)

        buf = BytesIO()
        doc.save(buf)
        buf.seek(0)
        return buf

    def render_pdf(
        self,
        content: ProposalContent,
        vertical: VERTICAL,
        tenant: TenantMeta,
    ) -> bytes:
        html = self._build_html(content, tenant)
        from weasyprint import HTML

        return HTML(string=html).write_pdf()

    def render_html_preview(
        self,
        content: ProposalContent,
        tenant: TenantMeta,
    ) -> str:
        return self._build_html(content, tenant)

    def _build_html(self, content: ProposalContent, tenant: TenantMeta) -> str:
        logo_html = (
            f'<img src="data:image/png;base64,{tenant.logo_png_b64}" height="50"/>'
            if tenant.logo_png_b64
            else ""
        )
        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"/><style>
  body {{ font-family: Arial, sans-serif; margin: 40px; color: #222; }}
  header {{ display: flex; justify-content: space-between; border-bottom: 2px solid #003399; padding-bottom: 12px; }}
  footer {{ margin-top: 40px; font-size: 10px; color: #666; text-align: center; }}
  pre {{ white-space: pre-wrap; font-family: Arial, sans-serif; }}
</style></head>
<body>
  <header>
    {logo_html}
    <div><strong>{tenant.name}</strong><br/>CNPJ: {tenant.cnpj}</div>
    <div>Gerado em: {content.generated_at.strftime("%d/%m/%Y")}</div>
  </header>
  <h2>Proposta Técnica e Comercial</h2>
  <pre>{content.content}</pre>
  <p><strong>Valor Global: R$ {content.price:,.2f}</strong></p>
  <p>Validade da Proposta: {content.validity_days} dias</p>
  <footer>Documento gerado pelo LicitaCerta AI — {tenant.name} | CNPJ {tenant.cnpj}</footer>
</body></html>"""
