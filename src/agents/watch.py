from __future__ import annotations

import contextlib
import os
import time
import uuid
from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from src.agents._gemini_utils import _calc_cost_gemini_flash, _extract_usage_gemini
from src.agents.model_router import ModelTier, get_llm
from src.config import settings
from src.observability import get_langfuse_handler

if TYPE_CHECKING:
    from src.gcp.bigquery import BigQueryWriter


class WatchAlert(BaseModel):
    alert_type: str
    urgency: str
    description: str
    deadline: str | None
    recommended_action: str
    human_decision_required: bool


class WatchResult(BaseModel):
    alerts: list[WatchAlert]
    next_deadline: str | None
    summary: str


SYSTEM_PROMPT = """Você é o Agente de Monitoramento (Watch) do LicitaCerta AI.
Analise o status atual da licitação e identifique alertas, prazos críticos
e mensagens do órgão que requerem ação.

## Contexto disponível

- `tender_schema`: objeto estruturado do edital (datas, prazos)
- `proposal_draft`: proposta já gerada (se disponível)
- `monitoring_data`: dados de monitoramento do portal (mensagens, atualizações)

## Regras

- `alerts`: liste todos os eventos que requerem atenção
  * `prazo_vencendo`: sessão de pregão, entrega de documentos, recursos
  * `mensagem_orgao`: comunicado oficial sobre esclarecimentos ou impugnações
  * `impugnacao`: impugnação recebida ou a ser enviada
  * `esclarecimento`: pedido de esclarecimento recebido
- `urgency`: "critical" se < 24h, "high" se < 3 dias, "medium" se < 7 dias, "low" se > 7 dias
- `human_decision_required`: true para qualquer ação que produza efeito externo
- `next_deadline`: próximo prazo crítico em ISO 8601; null se não houver
- `summary`: resumo em 1-2 frases do estado atual do monitoramento

Responda EXCLUSIVAMENTE no schema JSON fornecido."""


class WatchAgent:
    def __init__(self) -> None:
        self._llm = get_llm(ModelTier.CLASSIFY).with_structured_output(
            WatchResult, include_raw=True
        )
        self._bq: BigQueryWriter | None = None

    def _get_bq(self) -> BigQueryWriter | None:
        if not os.environ.get("GCP_PROJECT_ID"):
            return None
        if self._bq is None:
            from src.gcp.bigquery import BigQueryWriter
            self._bq = BigQueryWriter.from_env()
        return self._bq

    def _otel_span(self, name: str) -> Any:
        try:
            from opentelemetry import trace
            return trace.get_tracer("licitacerta.agents").start_as_current_span(name)
        except Exception:
            return contextlib.nullcontext()

    def _build_messages(self, context: dict) -> list:
        lines = [
            f"tender_schema: {context.get('tender_schema')}",
            f"proposal_draft: {context.get('proposal_draft')}",
            f"monitoring_data: {context.get('monitoring_data')}",
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
                agent_name="watch",
                model_id=settings.gemini_flash,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=latency_ms,
                cost_brl=_calc_cost_gemini_flash(tokens_in, tokens_out),
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

    def run(self, context: dict) -> WatchResult:
        run_id = context.get("run_id") or str(uuid.uuid4())
        tenant_id = context.get("tenant_id", "unknown")
        messages = self._build_messages(context)
        callbacks = self._get_callbacks(run_id)
        invoke_config = {"callbacks": callbacks} if callbacks else {}

        t0 = time.time()
        with self._otel_span("agent.watch"):
            result = self._llm.invoke(messages, config=invoke_config)
        latency_ms = int((time.time() - t0) * 1000)

        tokens_in, tokens_out = _extract_usage_gemini(result.get("raw"))
        self._log_bq(run_id, tenant_id, tokens_in, tokens_out, latency_ms)

        parsed = result.get("parsed")
        if parsed is None:
            raise ValueError(f"WatchAgent structured output failed: {result.get('parsing_error')}")
        return parsed

    async def arun(self, context: dict) -> WatchResult:
        run_id = context.get("run_id") or str(uuid.uuid4())
        tenant_id = context.get("tenant_id", "unknown")
        messages = self._build_messages(context)
        callbacks = self._get_callbacks(run_id)
        invoke_config = {"callbacks": callbacks} if callbacks else {}

        t0 = time.time()
        with self._otel_span("agent.watch"):
            result = await self._llm.ainvoke(messages, config=invoke_config)
        latency_ms = int((time.time() - t0) * 1000)

        tokens_in, tokens_out = _extract_usage_gemini(result.get("raw"))
        self._log_bq(run_id, tenant_id, tokens_in, tokens_out, latency_ms)

        parsed = result.get("parsed")
        if parsed is None:
            raise ValueError(f"WatchAgent structured output failed: {result.get('parsing_error')}")
        return parsed
