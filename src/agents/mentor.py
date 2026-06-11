"""MentorAgent — conversational mentor with SSE streaming and AlloyDB history.

ModelTier: GENERATE (Gemini 2.5 Pro).
Streaming: yields text chunks, then final [STRUCTURED] event with MentorResponse JSON.
"""
from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.model_router import ModelTier, get_llm
from src.schemas.mentor import MentorMessage, MentorResponse

logger = logging.getLogger(__name__)

_DISCLAIMER_JURIDICO = (
    "⚠️ Esta resposta é informativa e não substitui orientação jurídica especializada."
)

SYSTEM_PROMPT_TEMPLATE = """\
Você é o Mentor LicitaCerta, especialista sênior em licitações públicas brasileiras
(Lei 14.133/2021, Lei 13.303/2016, jurisprudência TCU).

Contexto da licitação atual (truncado):
{tender_state_json}

Perfil da empresa:
{tenant_profile_json}

Histórico recente:
{historico_resumo}

REGRAS OBRIGATÓRIAS:
- Cite sempre o artigo de lei ou cláusula do edital em afirmações jurídicas.
- Para tipo_resposta="juridico", preencha o campo `disclaimer`.
- acoes_sugeridas: máximo 3 ações, com rota quando aplicável.
- evidencias: cite página e trecho do edital quando relevante.
- Responda em português brasileiro, tom profissional mas acessível.
- Nunca invente artigos ou acórdãos — apenas cite o que o contexto suporta.

CLASSIFICAÇÃO DE TIPO:
- juridico: pergunta sobre leis, cláusulas ilegais, impugnação, recursos
- financeiro: margem, pricing, fluxo de caixa, antecipação
- operacional: documentação, prazos, portais, sistema
- estrategico: vantagem competitiva, probabilidade, ações prioritárias
- geral: qualquer outra pergunta

Responda apenas o campo `resposta` em linguagem natural fluída.
Retorne um objeto JSON com os campos: resposta, tipo_resposta, acoes_sugeridas, evidencias, confianca, disclaimer.
"""

_CONTEXT_MAX_CHARS = 32_000  # ~8k tokens @ 4 chars/token


def _truncate(text: str, max_chars: int = _CONTEXT_MAX_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [truncado]"


def _resumo_historico(historico: list[MentorMessage]) -> str:
    if not historico:
        return "(sem histórico)"
    lines = []
    for msg in historico[-10:]:  # últimas 10 mensagens
        role = "Usuário" if msg.role == "user" else "Mentor"
        lines.append(f"{role}: {msg.content[:200]}")
    return "\n".join(lines)


def _parse_mentor_response(raw_text: str) -> MentorResponse:
    """Extract JSON from raw LLM text, with graceful fallback."""
    try:
        start = raw_text.find("{")
        end = raw_text.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(raw_text[start:end])
            return MentorResponse(**data)
    except Exception:
        pass
    return MentorResponse(
        resposta=raw_text.strip(),
        tipo_resposta="geral",
        confianca=0.5,
    )


class MentorAgent:
    def __init__(self) -> None:
        self._llm = get_llm(ModelTier.GENERATE)

    async def stream(
        self,
        pergunta: str,
        historico: list[MentorMessage],
        tender_state: Any,
        tenant_profile: dict,
    ) -> AsyncGenerator[str, None]:
        """Yields text chunks, then a final '[STRUCTURED]{json}' event."""
        tender_json = _truncate(
            json.dumps(tender_state, ensure_ascii=False, default=str)
            if isinstance(tender_state, dict)
            else json.dumps(
                {k: str(v) for k, v in (tender_state or {}).items()},
                ensure_ascii=False,
            )
        )
        system_text = SYSTEM_PROMPT_TEMPLATE.format(
            tender_state_json=tender_json,
            tenant_profile_json=_truncate(
                json.dumps(tenant_profile or {}, ensure_ascii=False), 2000
            ),
            historico_resumo=_resumo_historico(historico),
        )

        messages = [
            SystemMessage(content=system_text),
            HumanMessage(content=pergunta),
        ]

        full_text = ""
        try:
            async for chunk in self._llm.astream(messages):
                delta = getattr(chunk, "content", "") or ""
                if delta:
                    full_text += delta
                    yield delta
        except Exception as exc:
            logger.warning("MentorAgent stream error: %s", exc)
            fallback = MentorResponse(
                resposta="Desculpe, ocorreu um erro ao processar sua pergunta. Tente novamente.",
                tipo_resposta="geral",
                confianca=0.0,
            )
            yield f"[STRUCTURED]{fallback.model_dump_json()}"
            return

        response = _parse_mentor_response(full_text)
        if response.tipo_resposta == "juridico" and not response.disclaimer:
            response.disclaimer = _DISCLAIMER_JURIDICO

        yield f"[STRUCTURED]{response.model_dump_json()}"
