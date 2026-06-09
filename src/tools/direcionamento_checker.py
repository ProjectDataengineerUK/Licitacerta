"""Detecção determinística de sinais de direcionamento e cartel em editais.

Parte determinística (sinais) + LLM only when score >= 40 (fundamentação).
Never raises — returns low-score result on any exception.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.schemas.market import CompetitiveContext
    from src.schemas.tender import TenderSchema

from src.schemas.direcionamento import DirecionamentoResult, NivelDirecionamento, SinalDetectado

logger = logging.getLogger(__name__)

FORBIDDEN_PHRASES = [
    "direcionado para",
    "fraudulento",
    "ilegal",
    "comprovou",
    "certamente",
    "constatado que",
    "evidente que",
]

# Sinais determinísticos com pesos (soma pode chegar a 1.0 = 100 pts)
SINAIS_DIRECIONAMENTO: dict[str, dict] = {
    "especificacao_unica": {
        "peso": 0.20,
        "descricao": "Especificação técnica única que favorece fornecedor específico",
    },
    "atestado_especifico": {
        "peso": 0.15,
        "descricao": "Exigência de atestado de capacidade técnica muito específica",
    },
    "certidao_inexistente": {
        "peso": 0.15,
        "descricao": "Exigência de certidão de órgão que não emite tal documento",
    },
    "prazo_impossivel": {
        "peso": 0.15,
        "descricao": "Prazo para proposta inviável para nova habilitação",
    },
    "publicacao_sexta_tarde": {
        "peso": 0.10,
        "descricao": "Publicação na sexta-feira após 17h",
    },
    "visita_tecnica": {
        "peso": 0.10,
        "descricao": "Visita técnica obrigatória com prazo curtíssimo",
    },
    "valor_referencia_suspeito": {
        "peso": 0.10,
        "descricao": "Valor de referência coincide com proposta de único fornecedor histórico",
    },
    "restricao_porte": {
        "peso": 0.05,
        "descricao": "Cláusula que restringe participação de ME/EPP sem justificativa",
    },
}

SINAIS_CARTEL: dict[str, dict] = {
    "revezamento_vitorias": {
        "peso": 0.30,
        "descricao": "Mesmo conjunto de empresas vence alternadamente em órgãos similares",
    },
    "lances_coordenados": {
        "peso": 0.30,
        "descricao": "Padrão de lances sugestivo de coordenação prévia",
    },
    "participacao_conjunta": {
        "peso": 0.20,
        "descricao": "Empresas do mesmo grupo econômico participam sem transparência",
    },
    "desistencias_suspeitas": {
        "peso": 0.20,
        "descricao": "Desistências coordenadas após abertura da sessão",
    },
}


def _is_sexta_tarde(data_publicacao: Any) -> bool:
    if data_publicacao is None:
        return False
    try:
        if isinstance(data_publicacao, str):
            from dateutil.parser import parse
            data_publicacao = parse(data_publicacao)
        return data_publicacao.weekday() == 4 and data_publicacao.hour >= 17
    except Exception:
        return False


def _check_sinais_tender(tender: "TenderSchema") -> list[SinalDetectado]:
    sinais: list[SinalDetectado] = []

    checks: dict[str, tuple[bool, str]] = {
        "especificacao_unica": (
            bool(getattr(tender, "especificacao_tem_marca", False) or getattr(tender, "exige_modelo_especifico", False)),
            str(getattr(tender, "exigencias_tecnicas", "") or ""),
        ),
        "atestado_especifico": (
            bool(getattr(tender, "atestado_cnae_restritivo", False) or getattr(tender, "atestado_valor_elevado", False)),
            "Exigência de atestado específico identificada",
        ),
        "certidao_inexistente": (
            bool(getattr(tender, "certidao_nao_padrao", False)),
            "Certidão não-padrão exigida",
        ),
        "prazo_impossivel": (
            (getattr(tender, "prazo_proposta_dias", None) or 99) < 5,
            f"Prazo proposta: {getattr(tender, 'prazo_proposta_dias', 'N/A')} dias",
        ),
        "publicacao_sexta_tarde": (
            _is_sexta_tarde(getattr(tender, "data_publicacao", None)),
            f"Publicação: {getattr(tender, 'data_publicacao', 'N/A')}",
        ),
        "visita_tecnica": (
            bool(getattr(tender, "visita_tecnica_obrigatoria", False))
            and (getattr(tender, "prazo_visita_dias", 99) or 99) < 3,
            "Visita técnica obrigatória com prazo < 3 dias",
        ),
        "valor_referencia_suspeito": (
            bool(getattr(tender, "valor_referencia_coincide_historico", False)),
            "Valor de referência coincidente com histórico de único fornecedor",
        ),
        "restricao_porte": (
            bool(getattr(tender, "restringe_me_epp", False))
            and not bool(getattr(tender, "justificativa_restricao", None)),
            "Restrição ME/EPP sem justificativa",
        ),
    }

    for codigo, (ativado, evidencia) in checks.items():
        if ativado:
            cfg = SINAIS_DIRECIONAMENTO[codigo]
            sinais.append(SinalDetectado(
                codigo=codigo,
                descricao=cfg["descricao"],
                peso=cfg["peso"],
                evidencia=str(evidencia)[:300],
            ))
    return sinais


def _check_sinais_cartel(competitive: "CompetitiveContext | None") -> list[SinalDetectado]:
    if not competitive or getattr(competitive, "data_insuficiente", True):
        return []
    sinais: list[SinalDetectado] = []
    if getattr(competitive, "concentracao_alta", False):
        sinais.append(SinalDetectado(
            codigo="revezamento_vitorias",
            descricao=SINAIS_CARTEL["revezamento_vitorias"]["descricao"],
            peso=SINAIS_CARTEL["revezamento_vitorias"]["peso"],
            evidencia=f"Concentração alta: dominante={getattr(competitive, 'cnpj_dominante', 'N/A')}",
        ))
    return sinais


def _identificar_beneficiario(tender: "TenderSchema", competitive: "CompetitiveContext | None") -> str | None:
    if competitive:
        cnpj_dom = getattr(competitive, "cnpj_dominante", None)
        if cnpj_dom:
            return cnpj_dom
    return None


async def _gerar_fundamentacao(sinais: list[SinalDetectado], tender: "TenderSchema") -> tuple[str, list[str]]:
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from src.agents.model_router import ModelTier, get_llm

        sinal_desc = "; ".join(f"{s.codigo} (peso {s.peso})" for s in sinais)
        prompt = (
            "Você é um especialista em licitações. Com base nos sinais detectados abaixo, "
            "redija uma fundamentação jurídica cautelosa para possível impugnação. "
            "Use SOMENTE linguagem de 'sinais de', 'indícios de'. JAMAIS use linguagem de certeza. "
            "Cite 2-3 acórdãos do TCU relevantes. Responda em português brasileiro.\n\n"
            f"Sinais: {sinal_desc}\n"
            f"Objeto: {getattr(tender, 'objeto', '')}"
        )
        llm = get_llm(ModelTier.CLASSIFY)
        resp = await llm.ainvoke([SystemMessage(content=""), HumanMessage(content=prompt)])
        text = resp.content if hasattr(resp, "content") else str(resp)
        _validate_language(text)
        precedentes = _extract_acordaos(text)
        return text, precedentes
    except Exception as exc:
        logger.warning("direcionamento_checker._gerar_fundamentacao: %s", exc)
        return None, []


def _validate_language(text: str) -> str:
    lower = text.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lower:
            raise ValueError(f"Linguagem proibida: '{phrase}'. Use 'sinais de' ou 'indícios de'.")
    return text


def _extract_acordaos(text: str) -> list[str]:
    import re
    return re.findall(r"Acórdão[\s\S]*?(?=Acórdão|$)", text)[:3]


def _recomendacao(nivel: str) -> str:
    if nivel == "alto":
        return "Sinais fortes de potencial direcionamento detectados. Recomenda-se avaliação de impugnação."
    if nivel == "medio":
        return "Sinais moderados detectados. Monitorar e considerar questionamentos pontuais."
    return "Nenhum sinal relevante de direcionamento identificado."


async def check(
    tender: "TenderSchema",
    competitive: "CompetitiveContext | None" = None,
) -> DirecionamentoResult:
    try:
        sinais = _check_sinais_tender(tender)
        sinais_cartel = _check_sinais_cartel(competitive)

        score = min(100.0, sum(s.peso for s in sinais) * 100)
        nivel: NivelDirecionamento = "alto" if score >= 60 else ("medio" if score >= 40 else "baixo")

        fingerprint = _identificar_beneficiario(tender, competitive) if score >= 40 else None

        fundamentacao = None
        precedentes: list[str] = []
        if score >= 40:
            fundamentacao, precedentes = await _gerar_fundamentacao(sinais, tender)

        return DirecionamentoResult(
            score=score,
            nivel=nivel,
            sinais_detectados=sinais,
            sinais_cartel=sinais_cartel,
            fingerprint_beneficiario=fingerprint,
            recomendacao=_recomendacao(nivel),
            fundamentacao_impugnacao=fundamentacao,
            precedentes_tcu=precedentes,
            impugnacao_recomendada=score >= 60,
        )
    except Exception as exc:
        logger.warning("direcionamento_checker.check falhou: %s", exc)
        return DirecionamentoResult(
            score=0.0,
            nivel="baixo",
            recomendacao="Análise de direcionamento indisponível.",
        )
