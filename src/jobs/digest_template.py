"""Template HTML do digest — inline CSS, responsivo, deep-link /runs/{run_id}."""
from __future__ import annotations

import html
from datetime import date


def _card(op, frontend_url: str) -> str:
    deep_link = f"{frontend_url}/runs/{html.escape(op.run_id)}"
    resumo = html.escape(op.resumo) if op.resumo else (
        "<em style='color:#9ca3af'>Resumo indisponível no momento.</em>"
    )
    valor = f"R$ {op.valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"""
    <tr><td style="padding:0 0 16px 0;">
      <table width="100%" cellpadding="0" cellspacing="0"
             style="border:1px solid #e5e7eb;border-radius:12px;background:#ffffff;">
        <tr><td style="padding:16px 20px;">
          <p style="margin:0 0 4px;font-size:15px;font-weight:600;color:#111827;">
            {html.escape(op.titulo)}
          </p>
          <p style="margin:0 0 8px;font-size:12px;color:#6b7280;">
            {html.escape(op.orgao)} &middot; {html.escape(op.uf)} &middot; {valor}
          </p>
          <p style="margin:0 0 14px;font-size:13px;line-height:1.5;color:#374151;">{resumo}</p>
          <a href="{deep_link}"
             style="display:inline-block;background:#2563eb;color:#ffffff;
                    text-decoration:none;font-size:13px;font-weight:600;
                    padding:9px 18px;border-radius:8px;">
            Ver análise completa &rarr;
          </a>
        </td></tr>
      </table>
    </td></tr>
    """


def build_digest_html(tenant_id: str, ops, d: date, frontend_url: str) -> str:
    cards = "".join(_card(o, frontend_url) for o in ops)
    data_fmt = d.strftime("%d/%m/%Y")
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:24px 0;">
    <tr><td align="center">
      <table width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">
        <tr><td style="padding:0 12px 16px;">
          <p style="margin:0;font-size:20px;font-weight:700;color:#111827;">LicitaCerta</p>
          <p style="margin:4px 0 0;font-size:13px;color:#6b7280;">
            Suas {len(ops)} melhores oportunidades &middot; {data_fmt}
          </p>
        </td></tr>
        <tr><td style="padding:0 12px;">
          <table width="100%" cellpadding="0" cellspacing="0">{cards}</table>
        </td></tr>
        <tr><td style="padding:8px 12px 0;">
          <p style="margin:0;font-size:11px;color:#9ca3af;line-height:1.5;">
            Você recebe este resumo porque ativou o Digest Diário.
            Ajuste suas preferências em
            <a href="{frontend_url}/config/digest" style="color:#2563eb;">configurações</a>.
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""
