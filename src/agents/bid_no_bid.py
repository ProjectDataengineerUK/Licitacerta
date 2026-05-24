from __future__ import annotations

import contextlib
import os
import time
import uuid
from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents._gemini_utils import _calc_cost_gemini_pro, _extract_usage_gemini
from src.agents.model_router import ModelTier, get_llm
from src.config import settings
from src.observability import get_langfuse_handler
from src.schemas.results import BidDecision

if TYPE_CHECKING:
    from src.gcp.bigquery import BigQueryWriter

SYSTEM_PROMPT = """Você é o Agente de Decisão Bid/No-Bid do LicitaCerta AI.
Sintetize todos os resultados anteriores e emita uma recomendação final sobre
se a empresa deve ou não participar desta licitação.

## Contexto disponível

- `tender_schema`: objeto estruturado do edital
- `eligibility`: resultado de elegibilidade (is_eligible, missing_documents)
- `compliance`: resultado de compliance (risk_level, blocking_issues, restrictive_clauses)
- `blacklist`: status de sanções (any_blocked)
- `pricing`: resultado de precificação (recommended_price, min_margin_pct, scenarios, blocking_issues)

## Regras de recomendação

- `"nao_participar"`: se blacklist.any_blocked=true OU eligibility.is_eligible=false
  OU compliance.risk_level="critical" OU pricing tem issue com severity "blocking"
- `"impugnar"`: se compliance.risk_level="critical" mas há fundamento legal para questionar
  judicialmente a restrição (cláusula restritiva sem amparo legal)
- `"pedir_esclarecimento"`: se há ambiguidades no edital resolvíveis antes da abertura da sessão
- `"participar_com_ressalvas"`: riscos médios/altos mas a oportunidade é viável comercialmente
- `"participar"`: cenário favorável — elegível, sem bloqueios, margem adequada, baixo risco

## Campos de saída

- `recommendation`: uma das 5 opções acima (obrigatório)
- `risk_level`: "high" se compliance "high" ou margem < 10%; "medium" se compliance "medium"
  ou margem 10-15%; "low" se compliance "low" e margem > 15%
- `expected_margin_pct`: valor de pricing.scenarios["realista"] se disponível; senão estimativa
- `conclusion`: síntese em 1-2 frases justificando a recomendação
- `blocking_issues`: repercuta aqui os blocking_issues que determinaram "nao_participar"
- `human_decision_required`: true para qualquer recomendação diferente de "participar" ou
  "nao_participar" (decisões intermediárias sempre merecem revisão humana)
- `recommended_action`: próximo passo concreto para o operador

Responda EXCLUSIVAMENTE no schema JSON fornecido."""


class BidNoBidAgent:
    def __init__(self) -> None:
        self._llm = get_llm(ModelTier.ANALYZE).with_structured_output(
            BidDecision, include_raw=True
        )
        self._bq: BigQueryWriter | None = None

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
            f"pricing: {context.get('pricing')}",
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
                agent_name="bid_no_bid",
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

    def run(self, context: dict) -> BidDecision:
        run_id = context.get("run_id") or str(uuid.uuid4())
        tenant_id = context.get("tenant_id", "unknown")
        messages = self._build_messages(context)
        callbacks = self._get_callbacks(run_id)
        invoke_config = {"callbacks": callbacks} if callbacks else {}

        t0 = time.time()
        with self._otel_span("agent.bid_no_bid"):
            result = self._llm.invoke(messages, config=invoke_config)
        latency_ms = int((time.time() - t0) * 1000)

        tokens_in, tokens_out = _extract_usage_gemini(result.get("raw"))
        self._log_bq(run_id, tenant_id, tokens_in, tokens_out, latency_ms)

        parsed = result.get("parsed")
        if parsed is None:
            raise ValueError(f"BidNoBidAgent structured output failed: {result.get('parsing_error')}")
        return parsed

    async def arun(self, context: dict) -> BidDecision:
        run_id = context.get("run_id") or str(uuid.uuid4())
        tenant_id = context.get("tenant_id", "unknown")
        messages = self._build_messages(context)
        callbacks = self._get_callbacks(run_id)
        invoke_config = {"callbacks": callbacks} if callbacks else {}

        t0 = time.time()
        with self._otel_span("agent.bid_no_bid"):
            result = await self._llm.ainvoke(messages, config=invoke_config)
        latency_ms = int((time.time() - t0) * 1000)

        tokens_in, tokens_out = _extract_usage_gemini(result.get("raw"))
        self._log_bq(run_id, tenant_id, tokens_in, tokens_out, latency_ms)

        parsed = result.get("parsed")
        if parsed is None:
            raise ValueError(f"BidNoBidAgent structured output failed: {result.get('parsing_error')}")
        return parsed
