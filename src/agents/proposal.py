from __future__ import annotations

import contextlib
import os
import threading
import time
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents._gemini_utils import _calc_cost_gemini_generate, _extract_usage_gemini
from src.agents.model_router import ModelTier, get_llm
from src.config import settings
from src.observability import get_langfuse_handler
from src.schemas.results import AgentMetric, ProposalDraft

if TYPE_CHECKING:
    from src.gcp.bigquery import BigQueryWriter

SYSTEM_PROMPT = """Você é o Agente de Proposta do LicitaCerta AI.
Gere a proposta comercial completa para envio ao órgão licitante.
Este agente é ativado SOMENTE após aprovação humana explícita.

Contexto recebido:
- tender_schema: objeto estruturado do edital
- pricing: resultado de precificação com preço recomendado e cenários
- bid_decision: decisão de participação
- human_approvals: histórico de aprovações humanas

Regras de geração:
- content: texto completo da proposta em formato adequado para pregão eletrônico,
  incluindo: identificação da empresa, descrição do objeto, preço unitário e total,
  prazo de entrega, validade da proposta, declarações obrigatórias (Lei 14.133/2021)
- price: usar pricing.recommended_price como base; ajustar conforme orientação humana
  registrada em human_approvals
- validity_days: padrão 60 dias se não especificado no edital
- attachments: listar documentos que devem ser anexados (certidões, atestados, etc.)
- approved_by: nome do aprovador do último human_approval
- generated_at: timestamp atual

Importante:
- A proposta deve ser factual, sem ambiguidades e em conformidade com o edital
- Incluir todas as declarações exigidas pelo órgão
- Usar linguagem formal e jurídica adequada

Responda EXCLUSIVAMENTE no schema JSON fornecido."""


class ProposalAgent:
    def __init__(self) -> None:
        self._llm = get_llm(ModelTier.GENERATE).with_structured_output(
            ProposalDraft, include_raw=True
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
                subgraph="execution",
                agent="proposal",
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
            f"pricing: {context.get('pricing')}",
            f"bid_decision: {context.get('bid_decision')}",
            f"human_approvals: {context.get('human_approvals')}",
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
                agent_name="proposal",
                model_id=settings.gemini_generate,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=latency_ms,
                cost_brl=_calc_cost_gemini_generate(tokens_in, tokens_out),
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

    def run(self, context: dict) -> ProposalDraft:
        run_id = context.get("run_id") or str(uuid.uuid4())
        tenant_id = context.get("tenant_id", "unknown")
        messages = self._build_messages(context)
        callbacks = self._get_callbacks(run_id)
        invoke_config = {"callbacks": callbacks} if callbacks else {}

        t0 = time.time()
        with self._otel_span("agent.proposal"):
            result = self._llm.invoke(messages, config=invoke_config)
        latency_ms = int((time.time() - t0) * 1000)

        tokens_in, tokens_out = _extract_usage_gemini(result.get("raw"))
        self._log_bq(run_id, tenant_id, tokens_in, tokens_out, latency_ms)
        self._set_last_metric(
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_brl=_calc_cost_gemini_generate(tokens_in, tokens_out),
            latency_ms=latency_ms,
            model_id=settings.gemini_generate,
        )

        parsed = result.get("parsed")
        if parsed is None:
            raise ValueError(f"ProposalAgent structured output failed: {result.get('parsing_error')}")
        return parsed

    async def arun(self, context: dict) -> ProposalDraft:
        run_id = context.get("run_id") or str(uuid.uuid4())
        tenant_id = context.get("tenant_id", "unknown")
        messages = self._build_messages(context)
        callbacks = self._get_callbacks(run_id)
        invoke_config = {"callbacks": callbacks} if callbacks else {}

        t0 = time.time()
        with self._otel_span("agent.proposal"):
            result = await self._llm.ainvoke(messages, config=invoke_config)
        latency_ms = int((time.time() - t0) * 1000)

        tokens_in, tokens_out = _extract_usage_gemini(result.get("raw"))
        self._log_bq(run_id, tenant_id, tokens_in, tokens_out, latency_ms)
        self._set_last_metric(
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_brl=_calc_cost_gemini_generate(tokens_in, tokens_out),
            latency_ms=latency_ms,
            model_id=settings.gemini_generate,
        )

        parsed = result.get("parsed")
        if parsed is None:
            raise ValueError(f"ProposalAgent structured output failed: {result.get('parsing_error')}")
        return parsed
