"""EstrategiaAgent — gera 5 ações estratégicas priorizadas pós-BidNoBid.

ModelTier: GENERATE (Gemini 2.5 Pro).
Curto-circuito: data_insuficiente=True sem bid_decision ou compliance.
"""
from __future__ import annotations

import logging
import time
import threading
import uuid
from datetime import datetime
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.model_router import ModelTier, get_llm
from src.config import settings
from src.schemas.estrategia import EstrategiaResult
from src.schemas.results import AgentMetric

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Você é um consultor sênior de licitações públicas brasileiras.
Dado o resultado completo da análise (BidNoBid, Compliance, Pricing, Competitivo),
gere exatamente 5 ações estratégicas priorizadas por impacto que a empresa pode tomar
para maximizar sua probabilidade de vitória.

Regras obrigatórias:
- Exatamente 5 ações. Mínimo 3 com prazo ≤ 7 dias.
- impacto_vitoria_pct: soma total ≤ 40 (realista).
- probabilidade_com_acoes_pct = probabilidade_sem_acoes_pct + soma(impacto_vitoria_pct).
- Clampar probabilidade_com_acoes_pct em 95%.
- acao_direta apenas para features existentes na plataforma.
- Nunca linguagem acusatória. Use "sinais de" para irregularidades.
- Responda em português brasileiro."""


def _calc_cost_brl(tokens_in: int, tokens_out: int) -> float:
    # Gemini 2.5 Pro: $1.25/M input, $10/M output; USD→BRL @ 5.70
    return (tokens_in * 1.25 + tokens_out * 10) / 1_000_000 * 5.70


def _extract_usage(raw: Any) -> tuple[int, int]:
    try:
        usage = raw.response_metadata.get("usage", {})
        return usage.get("input_tokens", 0), usage.get("output_tokens", 0)
    except Exception:
        return 0, 0


class EstrategiaAgent:
    def __init__(self) -> None:
        self._llm = get_llm(ModelTier.GENERATE).with_structured_output(
            EstrategiaResult, include_raw=True
        )
        self._last_metric: AgentMetric | None = None
        self._metric_lock = threading.Lock()

    def get_last_metric(self) -> AgentMetric | None:
        with self._metric_lock:
            m = self._last_metric
            self._last_metric = None
            return m

    def _set_last_metric(self, tokens_in: int, tokens_out: int, cost_brl: float, latency_ms: int) -> None:
        with self._metric_lock:
            self._last_metric = AgentMetric(
                subgraph="decision",
                agent="estrategia",
                metric_name="cost_brl",
                value=cost_brl,
                timestamp=datetime.utcnow(),
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_brl=cost_brl,
                latency_ms=latency_ms,
                model_id=settings.gemini_pro,
            )

    def _build_messages(self, context: dict) -> list:
        tender = context.get("tender_schema")
        bid = context.get("bid_decision")
        compliance = context.get("compliance")
        pricing = context.get("pricing")
        cc = context.get("competitive_context")

        parts: list[str] = []
        if tender:
            parts.append(f"objeto: {getattr(tender, 'objeto', '')}")
            parts.append(f"valor_estimado: {getattr(tender, 'valor_estimado', '')}")
        if bid:
            parts.append(f"bid_recommendation: {getattr(bid, 'recommendation', '')}")
            parts.append(f"bid_confidence: {getattr(bid, 'confidence', '')}")
            parts.append(f"bid_risk: {getattr(bid, 'risk_level', '')}")
            parts.append(f"expected_margin_pct: {getattr(bid, 'expected_margin_pct', '')}")
        if compliance:
            parts.append(f"compliance_risk: {getattr(compliance, 'risk_level', '')}")
            issues = getattr(compliance, "blocking_issues", [])
            if issues:
                parts.append(f"blocking_issues: {[getattr(i, 'description', '') for i in issues]}")
        if pricing:
            parts.append(f"recommended_price: {getattr(pricing, 'recommended_price', '')}")
            parts.append(f"margin_pct: {getattr(pricing, 'min_margin_pct', '')}")
        if cc and not getattr(cc, "data_insuficiente", True):
            parts.append(f"resumo_competitivo: {getattr(cc, 'resumo', '')}")
            bench = getattr(cc, "price_benchmark", None)
            if bench and not getattr(bench, "data_insuficiente", True):
                parts.append(f"benchmark_p75: {getattr(bench, 'percentil_75', '')}")

        run_id = context.get("run_id", "{run_id}")
        parts.append(f"run_id: {run_id}")

        return [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content="\n".join(parts)),
        ]

    async def arun(self, context: dict) -> EstrategiaResult:
        bid = context.get("bid_decision")
        compliance = context.get("compliance")
        if not bid or not compliance:
            return EstrategiaResult(
                probabilidade_sem_acoes_pct=0.0,
                probabilidade_com_acoes_pct=0.0,
                acoes=[],
                resumo_executivo="Dados insuficientes para estratégia.",
                data_insuficiente=True,
            )

        messages = self._build_messages(context)
        t0 = time.time()
        result = await self._llm.ainvoke(messages)
        latency_ms = int((time.time() - t0) * 1000)

        tokens_in, tokens_out = _extract_usage(result.get("raw"))
        cost_brl = _calc_cost_brl(tokens_in, tokens_out)
        self._set_last_metric(tokens_in, tokens_out, cost_brl, latency_ms)

        parsed: EstrategiaResult | None = result.get("parsed")
        if parsed is None:
            logger.warning("EstrategiaAgent structured output failed")
            return EstrategiaResult(
                probabilidade_sem_acoes_pct=0.0,
                probabilidade_com_acoes_pct=0.0,
                acoes=[],
                resumo_executivo="Falha ao gerar estratégia.",
                data_insuficiente=True,
            )

        # Enforce AT-006: clamp to 95%
        parsed.probabilidade_com_acoes_pct = min(95.0, parsed.probabilidade_com_acoes_pct)
        # Enforce AT-002: max 5 actions
        parsed.acoes = parsed.acoes[:5]
        return parsed
