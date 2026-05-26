from __future__ import annotations

import contextlib
import os
import threading
import time
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents._gemini_utils import _calc_cost_gemini_pro, _extract_usage_gemini
from src.agents.model_router import ModelTier, get_llm
from src.config import settings
from src.observability import get_langfuse_handler
from src.schemas.results import AgentMetric, PricingResult

if TYPE_CHECKING:
    from src.gcp.bigquery import BigQueryWriter

SYSTEM_PROMPT = """Você é o Agente de Precificação do LicitaCerta AI.
Analise o edital e os resultados de validação para calcular custo estimado,
margem mínima e preço recomendado de proposta.

## Contexto disponível

- `tender_schema`: objeto estruturado do edital (valor_estimado, prazo_pagamento_dias, objeto, modalidade)
- `eligibility`: resultado de elegibilidade (is_eligible, missing_documents)
- `compliance`: resultado de compliance (risk_level, blocking_issues)
- `blacklist`: status de sanções (any_blocked)
- `company_cnpj`: CNPJ da empresa participante

## Regras de precificação

- `cost_estimate`: estime o custo direto em Reais com base no valor_estimado do edital
  e no tipo de objeto (produto vs. serviço). Se valor_estimado indisponível, use 0.
- `min_margin_pct`: margem mínima aceitável considerando risco do compliance e prazo de pagamento:
  * risk_level "critical" ou "high" → min_margin_pct >= 25
  * risk_level "medium" → min_margin_pct >= 18
  * risk_level "low" → min_margin_pct >= 10
  * prazo_pagamento_dias > 60 → adicionar 3pp à margem (risco de capital de giro)
- `recommended_price`: preço sugerido = cost_estimate / (1 - min_margin_pct / 100)
- `scenarios`: três entradas obrigatórias com as chaves exatas "pessimista", "realista", "otimista"
  (valores em Reais, sem formatação)
- `conclusion`: síntese em 1-2 frases sobre a viabilidade financeira
- `blocking_issues`: se cost_estimate > valor_estimado, criar issue com severity "blocking"
- `human_decision_required`: true se margem esperada < 5% OU risk_level "critical"
- `recommended_action`: "Usar preço realista" / "Revisar margem com gestor" / "Não participar"

Responda EXCLUSIVAMENTE no schema JSON fornecido."""


class PricingAgent:
    def __init__(self) -> None:
        self._llm = get_llm(ModelTier.ANALYZE).with_structured_output(
            PricingResult, include_raw=True
        )
        self._bq: BigQueryWriter | None = None
        self._last_metric: AgentMetric | None = None
        self._metric_lock = threading.Lock()

    def _set_last_metric(
        self,
        *,
        tokens_in: int,
        tokens_out: int,
        cost_brl: float,
        latency_ms: int,
        model_id: str,
    ) -> None:
        with self._metric_lock:
            self._last_metric = AgentMetric(
                subgraph="decision",
                agent="pricing",
                metric_name="cost_brl",
                value=cost_brl,
                timestamp=datetime.utcnow(),
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_brl=cost_brl,
                latency_ms=latency_ms,
                model_id=model_id,
            )

    def get_last_metric(self) -> AgentMetric | None:
        with self._metric_lock:
            m = self._last_metric
            self._last_metric = None
            return m

    def _get_bq(self) -> BigQueryWriter | None:
        if not os.environ.get("GCP_PROJECT_ID"):
            return None
        if self._bq is None:
            from src.gcp.bigquery import BigQueryWriter
            self._bq = BigQueryWriter.from_env()
        return self._bq

    def _otel_span(self, name: str):
        try:
            from opentelemetry import trace
            return trace.get_tracer("licitacerta.agents").start_as_current_span(name)
        except Exception:
            return contextlib.nullcontext()

    def _build_messages(self, context: dict) -> list:
        lines = [
            f"tender_schema: {context.get('tender_schema')}",
            f"eligibility: {context.get('eligibility')}",
            f"compliance: {context.get('compliance')}",
            f"blacklist: {context.get('blacklist')}",
            f"company_cnpj: {context.get('company_cnpj', '')}",
        ]
        return [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content="\n".join(lines)),
        ]

    def _log_bq(self, run_id: str, tenant_id: str, tokens_in: int, tokens_out: int, latency_ms: int) -> None:
        bq = self._get_bq()
        if bq is None:
            return
        try:
            bq.insert_agent_run(
                run_id=run_id,
                tenant_id=tenant_id,
                agent_name="pricing",
                model_id=settings.gemini_pro,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=latency_ms,
                cost_brl=_calc_cost_gemini_pro(tokens_in, tokens_out),
                eval_score=None,
            )
        except Exception:
            pass

    def _get_callbacks(self, run_id: str) -> list:
        try:
            handler = get_langfuse_handler(run_id)
            return [handler] if handler else []
        except Exception:
            return []

    def run(self, context: dict) -> PricingResult:
        run_id = context.get("run_id") or str(uuid.uuid4())
        tenant_id = context.get("tenant_id", "unknown")
        messages = self._build_messages(context)
        callbacks = self._get_callbacks(run_id)
        invoke_config = {"callbacks": callbacks} if callbacks else {}

        t0 = time.time()
        with self._otel_span("agent.pricing"):
            result = self._llm.invoke(messages, config=invoke_config)
        latency_ms = int((time.time() - t0) * 1000)

        tokens_in, tokens_out = _extract_usage_gemini(result.get("raw"))
        self._log_bq(run_id, tenant_id, tokens_in, tokens_out, latency_ms)
        self._set_last_metric(
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_brl=_calc_cost_gemini_pro(tokens_in, tokens_out),
            latency_ms=latency_ms,
            model_id=settings.gemini_pro,
        )

        parsed = result.get("parsed")
        if parsed is None:
            raise ValueError(f"PricingAgent structured output failed: {result.get('parsing_error')}")
        return parsed

    async def arun(self, context: dict) -> PricingResult:
        run_id = context.get("run_id") or str(uuid.uuid4())
        tenant_id = context.get("tenant_id", "unknown")
        messages = self._build_messages(context)
        callbacks = self._get_callbacks(run_id)
        invoke_config = {"callbacks": callbacks} if callbacks else {}

        t0 = time.time()
        with self._otel_span("agent.pricing"):
            result = await self._llm.ainvoke(messages, config=invoke_config)
        latency_ms = int((time.time() - t0) * 1000)

        tokens_in, tokens_out = _extract_usage_gemini(result.get("raw"))
        self._log_bq(run_id, tenant_id, tokens_in, tokens_out, latency_ms)
        self._set_last_metric(
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_brl=_calc_cost_gemini_pro(tokens_in, tokens_out),
            latency_ms=latency_ms,
            model_id=settings.gemini_pro,
        )

        parsed = result.get("parsed")
        if parsed is None:
            raise ValueError(f"PricingAgent structured output failed: {result.get('parsing_error')}")
        return parsed
