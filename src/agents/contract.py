from __future__ import annotations

import contextlib
import os
import threading
import time
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from src.agents._gemini_utils import _calc_cost_gemini_pro, _extract_usage_gemini
from src.agents.model_router import ModelTier, get_llm
from src.config import settings
from src.observability import get_langfuse_handler
from src.schemas.results import AgentMetric

if TYPE_CHECKING:
    from src.gcp.bigquery import BigQueryWriter


class ContractObligation(BaseModel):
    description: str
    due_date: str | None
    recurrent: bool
    status: str  # pending, completed, overdue


class ContractResult(BaseModel):
    contract_status: str  # active, completed, suspended, terminated
    obligations: list[ContractObligation]
    next_payment_date: str | None
    reajuste_due: bool
    reajuste_index: str | None
    warnings: list[str]
    human_decision_required: bool
    recommended_action: str


SYSTEM_PROMPT = """Você é o Agente de Acompanhamento de Contratos do LicitaCerta AI.
Analise o contrato firmado e monitore obrigações, pagamentos, reajustes e vencimentos.

Contexto recebido:
- tender_schema: objeto do edital (base do contrato)
- proposal_draft: proposta vencedora
- contract_data: dados do contrato firmado (valor, prazo, cláusulas, pagamentos realizados)

Regras:
- contract_status: status atual do contrato
- obligations: todas as obrigações contratuais com prazo e status
- next_payment_date: próxima data de pagamento esperada
- reajuste_due: true se há reajuste contratual pendente
- reajuste_index: índice de reajuste (IPCA, INPC, IGP-M, etc.)
- warnings: alertas sobre vencimentos, inadimplência, necessidade de aditivos
- human_decision_required: true para negociações, aditivos ou disputas

Responda EXCLUSIVAMENTE no schema JSON fornecido."""


class ContractAgent:
    def __init__(self) -> None:
        self._llm = get_llm(ModelTier.ANALYZE).with_structured_output(
            ContractResult, include_raw=True
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
                subgraph="post_award",
                agent="contract",
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
            f"proposal_draft: {context.get('proposal_draft')}",
            f"contract_data: {context.get('contract_data')}",
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
                agent_name="contract",
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

    def run(self, context: dict) -> ContractResult:
        run_id = context.get("run_id") or str(uuid.uuid4())
        tenant_id = context.get("tenant_id", "unknown")
        messages = self._build_messages(context)
        callbacks = self._get_callbacks(run_id)
        invoke_config = {"callbacks": callbacks} if callbacks else {}

        t0 = time.time()
        with self._otel_span("agent.contract"):
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
            raise ValueError(f"ContractAgent structured output failed: {result.get('parsing_error')}")
        return parsed

    async def arun(self, context: dict) -> ContractResult:
        run_id = context.get("run_id") or str(uuid.uuid4())
        tenant_id = context.get("tenant_id", "unknown")
        messages = self._build_messages(context)
        callbacks = self._get_callbacks(run_id)
        invoke_config = {"callbacks": callbacks} if callbacks else {}

        t0 = time.time()
        with self._otel_span("agent.contract"):
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
            raise ValueError(f"ContractAgent structured output failed: {result.get('parsing_error')}")
        return parsed
