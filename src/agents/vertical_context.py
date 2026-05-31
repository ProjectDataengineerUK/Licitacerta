"""VERTICALIZACAO — contexto especializado por setor.

Blocos determinísticos (sem LLM): registry de contexto por vertical, checklist
de habilitação e detecção/score de compatibilidade vertical a partir do texto do
edital. A injeção destes blocos nos system prompts dos agentes e o RAG de
acórdãos TCU curados por vertical são a etapa seguinte.
"""
from __future__ import annotations

from src.schemas.tender import TenderVerticalMatch

Vertical = str  # "TI_SOFTWARE" | "LIMPEZA_CONSERVACAO" | "OBRAS_ENGENHARIA" | "OUTRO"

# --------------------------------------------------------------------------- #
# Registry de contexto por vertical
# --------------------------------------------------------------------------- #
VERTICAL_CONTEXT: dict[str, dict] = {
    "TI_SOFTWARE": {
        "label": "TI & Software",
        "compliance_extra": (
            "Em contratos de TI, verifique: certificações específicas (ISO 27001, CMMI) "
            "sem justificativa; especificação de marcas (Microsoft, SAP) sem permitir "
            "equivalentes; prazo de implementação incompatível; atestado de capacidade "
            "técnica com volume que restringe ME/EPP. Acórdãos TCU: 2500/2015, 1284/2023, 1510/2021."
        ),
        "habilitacao_extra": [
            "atestado_capacidade_tecnica_ti",
            "responsavel_tecnico_formacao_ti",
        ],
        "pricing_extra": "Inclua horas-homem, custos de infraestrutura cloud e licenças de terceiros.",
        "keywords": [
            "software", "sistema", "licença", "licenca", "desenvolvimento", "suporte técnico",
            "suporte tecnico", "cloud", "nuvem", "servidor", "banco de dados", "ti", "tecnologia da informação",
            "tecnologia da informacao", "aplicativo", "erp",
        ],
    },
    "LIMPEZA_CONSERVACAO": {
        "label": "Limpeza & Conservação",
        "compliance_extra": (
            "Em limpeza/conservação, verifique: número mínimo de funcionários sem justificativa; "
            "planilha de custos de mão-de-obra (piso da categoria, encargos, vale-transporte); "
            "Convenção Coletiva vigente; equipamentos específicos sem equivalentes. "
            "Acórdãos TCU: 1214/2013, 1903/2015."
        ),
        "habilitacao_extra": [
            "planilha_custos_mao_de_obra",
            "convencao_coletiva_vigente",
            "atestado_capacidade_tecnica_limpeza",
        ],
        "pricing_extra": (
            "Calcule pela composição de custos de mão-de-obra: salário + encargos "
            "(FGTS, INSS, férias, 13º) + vale-transporte + uniforme + EPI."
        ),
        "keywords": [
            "limpeza", "conservação", "conservacao", "asseio", "portaria", "copeiragem",
            "higienização", "higienizacao", "zeladoria", "jardinagem",
        ],
    },
    "OBRAS_ENGENHARIA": {
        "label": "Obras & Engenharia",
        "compliance_extra": (
            "Em obras, verifique: planilha orçamentária base SINAPI; registro CREA do "
            "responsável técnico; ART obrigatória; BDI dentro dos limites TCU "
            "(Acórdão 2.369/2011); prazo de execução vs. complexidade (Acórdão 2696/2022)."
        ),
        "habilitacao_extra": [
            "registro_crea_responsavel_tecnico",
            "capacidade_tecnica_obras",
            "capital_social_minimo_10pct_valor_obra",
        ],
        "pricing_extra": "Use planilha SINAPI; calcule BDI conforme Acórdão TCU 2.369/2011 (limite ~22-28%).",
        "keywords": [
            "obra", "obras", "construção", "construcao", "reforma", "engenharia",
            "edificação", "edificacao", "pavimentação", "pavimentacao", "crea", "art",
            "sinapi", "alvenaria", "infraestrutura viária",
        ],
    },
}

_BASE_HABILITACAO = [
    "habilitacao_juridica",
    "regularidade_fiscal_trabalhista",
    "qualificacao_economico_financeira",
]


def get_vertical_context(vertical: str | None) -> dict:
    """Retorna o bloco de contexto da vertical (ou vazio para None/'OUTRO')."""
    if not vertical:
        return {}
    return VERTICAL_CONTEXT.get(vertical.upper(), {})


def system_prompt_suffix(vertical: str | None) -> str:
    """Sufixo a injetar no system prompt do agente de compliance."""
    ctx = get_vertical_context(vertical)
    extra = ctx.get("compliance_extra")
    return f"\n\n[Contexto setorial — {ctx.get('label', vertical)}]\n{extra}" if extra else ""


def habilitacao_checklist(vertical: str | None) -> list[str]:
    """Checklist de habilitação: base + exigências específicas da vertical."""
    ctx = get_vertical_context(vertical)
    return [*_BASE_HABILITACAO, *ctx.get("habilitacao_extra", [])]


def detect_vertical(text: str) -> tuple[str | None, float]:
    """Detecta a vertical dominante no texto por palavras-chave.

    Retorna (vertical, score) onde score = hits_da_top / total_hits (0..1).
    """
    low = (text or "").lower()
    hits: dict[str, int] = {}
    for vertical, ctx in VERTICAL_CONTEXT.items():
        n = sum(1 for kw in ctx["keywords"] if kw in low)
        if n:
            hits[vertical] = n
    if not hits:
        return None, 0.0
    total = sum(hits.values())
    top = max(hits, key=lambda k: hits[k])
    return top, hits[top] / total


def vertical_match(text: str, tenant_vertical: str | None) -> TenderVerticalMatch:
    """Compatibilidade entre o edital e a vertical do tenant."""
    detected, det_score = detect_vertical(text)
    tenant = tenant_vertical.upper() if tenant_vertical else None

    if detected is None:
        return TenderVerticalMatch(
            vertical_detectada=None,
            score_compatibilidade=0.5,
            alerta_fora_do_setor=False,
            motivo="Não foi possível identificar a vertical do edital.",
        )

    if tenant is None or tenant == "OUTRO":
        return TenderVerticalMatch(
            vertical_detectada=detected,
            score_compatibilidade=det_score,
            alerta_fora_do_setor=False,
            motivo=f"Edital identificado como {detected}; tenant sem vertical definida.",
        )

    if detected == tenant:
        return TenderVerticalMatch(
            vertical_detectada=detected,
            score_compatibilidade=det_score,
            alerta_fora_do_setor=False,
            motivo=f"Edital compatível com a vertical do tenant ({tenant}).",
        )

    fora = det_score >= 0.5
    return TenderVerticalMatch(
        vertical_detectada=detected,
        score_compatibilidade=round(1 - det_score, 2) if fora else 0.5,
        alerta_fora_do_setor=fora,
        motivo=f"Edital parece ser de {detected}, mas o tenant atua em {tenant}.",
    )
